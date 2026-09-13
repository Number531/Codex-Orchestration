import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import tomllib
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalog_check', PACKAGE / 'test/check_catalog.py')
catalog_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_check)


class PackageTests(unittest.TestCase):
    def test_portable_manifest_and_compatibility_agree(self):
        # Agent Plugins 1.0.0 closed manifest contract, pinned to its canonical schema.
        # https://agent-plugins.org/schemas/1.0.0/plugin.schema.json
        manifest = json.loads((PACKAGE / 'plugin.json').read_text())
        permitted = {'$schema','name','version','description','author','homepage','repository','license','keywords','extensions'}
        self.assertFalse(set(manifest) - permitted)
        self.assertEqual(manifest['$schema'], 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json')
        self.assertRegex(manifest['name'], r'^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$')
        self.assertLessEqual(len(manifest['name']), 64)
        self.assertRegex(manifest['version'], r'^\d+\.\d+\.\d+$')
        self.assertEqual(manifest['name'], PACKAGE.name)
        self.assertFalse(set(manifest['author']) - {'name','email','url'})
        compat = json.loads((PACKAGE / '.codex-plugin/plugin.json').read_text())
        for key in ['name','version','author','description','license']:
            self.assertEqual(manifest[key], compat[key])
        self.assertEqual(manifest['license'], 'MIT')
        self.assertEqual((PACKAGE / 'LICENSE').read_bytes(), (PACKAGE.parents[1] / 'LICENSE').read_bytes())
        self.assertEqual(manifest['extensions']['com.openai']['interface'], compat['interface'])
        self.assertEqual(compat['interface']['displayName'], 'Codex-Orchestration')
        self.assertFalse((PACKAGE / 'hooks').exists(), 'No implicit plugin-hook loading contract')

    def test_skills_are_direct_children_self_contained_and_portable(self):
        skills = list((PACKAGE / 'skills').glob('*/SKILL.md'))
        self.assertEqual({s.parent.name for s in skills}, {'orchestration-setup','orchestration-delivery','orchestration-review'})
        for skill in skills:
            text = skill.read_text()
            self.assertTrue(text.startswith('---\n'))
            self.assertIn('name: '+skill.parent.name+'\n', text)
            self.assertRegex(text, r'(?m)^description: .{40,}$')
            self.assertNotIn('/Users/', text)
            self.assertNotIn('.durable-agent/', text)
            self.assertNotIn('deep-plan', text)
        self.assertTrue((PACKAGE / 'scripts/setup.py').is_file())

    def test_exact_role_bindings_pins_and_nesting_guidance(self):
        project = PACKAGE / 'assets/project'
        config = tomllib.loads((project / '.codex/config.toml').read_text())
        expected = {'default':('gpt-5.6-luna','max','read-only'), 'explorer':('gpt-5.6-luna','max','read-only'),
                    'worker':('gpt-5.6-terra','high','workspace-write'), 'implementer':('gpt-5.6-terra','high','workspace-write'),
                    'auditor':('gpt-5.6-sol','high','read-only'), 'verifier':('gpt-5.6-terra','medium','read-only')}
        registrations = {k:v for k,v in config['agents'].items() if isinstance(v,dict)}
        self.assertEqual(set(registrations), set(expected))
        self.assertEqual(config['agents']['default_subagent_model'], 'gpt-5.6-luna')
        for name, pins in expected.items():
            binding = registrations[name]
            self.assertEqual(binding['config_file'], 'agents/'+name+'.toml')
            profile = tomllib.loads((project / '.codex' / binding['config_file']).read_text())
            self.assertEqual(profile['name'], name)
            self.assertEqual(tuple(profile[k] for k in ['model','model_reasoning_effort','sandbox_mode']), pins)
            self.assertIn('Do not create subagents', profile['developer_instructions'])
            self.assertNotRegex(profile['developer_instructions'], r'Feature-implementation-cycle|deep-plan|tracer|/Users/')
        self.assertEqual(json.loads((project/'.codex/delegation-guard.json').read_text()), {'enabled':False})
        self.assertEqual(json.loads((project/'.codex/delegation-policy.json').read_text())['allowed_models'], ['gpt-5.6-luna','gpt-5.6-terra','gpt-5.6-sol'])

    def test_runtime_inventory_contains_no_caches_symlinks_or_personal_paths(self):
        total = 0
        for base in ['assets','scripts','skills','.codex-plugin']:
            for file in (PACKAGE/base).rglob('*'):
                self.assertFalse(file.is_symlink(), str(file))
                self.assertNotIn(file.name, {'auth.json','models_cache.json','__pycache__','.DS_Store'})
                if file.is_file():
                    data = file.read_bytes(); total += len(data)
                    self.assertLessEqual(len(data), 1024*1024)
                    self.assertNotIn(b'/Users/', data)
        self.assertLess(total, 1024*1024)

    def test_catalog_checker_accepts_valid_and_rejects_broken_integration(self):
        with tempfile.TemporaryDirectory(prefix='orchestration-catalog-') as scratch:
            root = Path(scratch)
            shutil.copytree(PACKAGE, root/'plugins/codex-orchestration', ignore=shutil.ignore_patterns('__pycache__'))
            file = root/'.agents/plugins/marketplace.json'; file.parent.mkdir(parents=True)
            catalog = {'name':'codex-orchestration', 'plugins':[{'name':'codex-orchestration','source':{'source':'local','path':'./plugins/codex-orchestration'},'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Productivity','version':'0.2.2'}]}
            file.write_text(json.dumps(catalog)); catalog_check.check(root)
            catalog['plugins'][0]['source']['path']='./missing'
            file.write_text(json.dumps(catalog))
            with self.assertRaises(AssertionError): catalog_check.check(root)
            catalog['plugins'][0]['source']['path']='./plugins/codex-orchestration'
            catalog['plugins'][0]['version']='9.9.9'
            file.write_text(json.dumps(catalog))
            with self.assertRaises(AssertionError): catalog_check.check(root)
            catalog['plugins'][0]['version']='0.2.2'
            catalog['plugins'].append(catalog['plugins'][0])
            file.write_text(json.dumps(catalog))
            with self.assertRaises(AssertionError): catalog_check.check(root)


if __name__ == '__main__':
    unittest.main()
