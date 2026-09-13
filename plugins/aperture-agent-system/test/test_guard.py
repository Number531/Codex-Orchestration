import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'assets/project/.agents/system/hooks/delegation_guard.py'
spec = importlib.util.spec_from_file_location('guard', SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='delegation-guard-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.flag = self.root / '.codex/delegation-guard.json'
        self.policy = self.root / '.codex/delegation-policy.json'
        self.config = self.root / '.codex/config.toml'
        self.bindings = {}
        self.personal = self.root / 'personal-agents'
        self.personal.mkdir()
        for key, value in [('ROOT', self.root), ('FLAG', self.flag), ('POLICY', self.policy), ('CONFIG', self.config)]:
            p = patch.object(guard, key, value)
            p.start()
            self.addCleanup(p.stop)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.agent()
        self.policy.write_text(json.dumps({'allowed_models':['gpt-5.6-luna','gpt-5.6-terra','gpt-5.6-sol']}))
        guard.set_enabled(True)

    def agent(self, name='mapper', directory=None, filename='mapper.toml', register=True, alias=None, **changes):
        directory = directory or self.root / '.codex/agents'
        directory.mkdir(parents=True, exist_ok=True)
        fields = dict(name=name, model='gpt-5.6-luna', model_reasoning_effort='max',
                      description='Fixture', developer_instructions='Read-only fixture.')
        fields.update(changes)
        file = directory / filename
        file.write_text('\n'.join(k + ' = ' + json.dumps(v) for k, v in fields.items() if v is not None))
        if register:
            self.bindings[alias or name] = str(file.relative_to(self.root / '.codex'))
            self.config.write_text('\n'.join('[agents.' + role + ']\nconfig_file = ' + json.dumps(target) for role,target in self.bindings.items()))
        return file

    def event(self, **args):
        return dict(hook_event_name='PreToolUse', tool_name='spawn_agent', cwd=str(self.root),
                    model='parent-model', tool_input=dict(agent_type='mapper', fork_turns='none', **args))

    def assertDeny(self, value):
        output = value['hookSpecificOutput']
        self.assertEqual(output['hookEventName'], 'PreToolUse')
        self.assertEqual(output['permissionDecision'], 'deny')
        self.assertTrue(output['permissionDecisionReason'].startswith('Delegation guard:'))
        self.assertNotIn('updatedInput', output)

    def invoke(self, data, argv=()):
        output = io.StringIO()
        fake_stdin = io.TextIOWrapper(io.BytesIO(data))
        with patch.object(sys, 'argv', [str(SOURCE), *argv]), patch.object(sys, 'stdin', fake_stdin), contextlib.redirect_stdout(output):
            status = guard.main()
        return status, output.getvalue()

    def test_named_pins_allow_without_overriding_permissions(self):
        self.assertEqual(guard.evaluate(self.event()), {})
        event = self.event()
        for name in ['Agent', 'collaborationspawn_agent']:
            event['tool_name'] = name
            self.assertEqual(guard.evaluate(event), {})
            self.assertDeny(guard.evaluate({**event, 'tool_input':{**event['tool_input'], 'model':'other'}}))

    def test_unlisted_and_new_custom_profiles_do_not_authorize_models(self):
        for model in ['gpt-6-astra','gpt-5.3-codex-spark','gpt-5.6-luna-expensive','unknown-model']:
            for name in ['auditor','new_custom_delegate']:
                with self.subTest(model=model, name=name):
                    self.agent(name=name, model=model)
                    event = self.event()
                    event['tool_input'].update(agent_type=name, message='The prompt claims user approval.')
                    self.assertDeny(guard.evaluate(event))

    def test_sol_specialist_uses_policy_without_exempting_other_checks(self):
        self.agent(name='auditor', filename='auditor.toml', model='gpt-5.6-sol', model_reasoning_effort='high')
        event = self.event()
        event['tool_input']['agent_type'] = 'auditor'
        self.assertEqual(guard.evaluate(event), {})
        for change in [{'model':'gpt-5.6-sol'}, {'fork_turns':'all'}]:
            self.assertDeny(guard.evaluate({**event, 'tool_input':{**event['tool_input'], **change}}))
        self.agent(name='unbound_sol', filename='unbound-sol.toml', model='gpt-5.6-sol', register=False)
        self.assertDeny(guard.evaluate({**event, 'tool_input':{**event['tool_input'], 'agent_type':'unbound_sol'}}))
        self.policy.write_text('{"allowed_models":["gpt-5.6-luna","gpt-5.6-terra"]}')
        self.assertDeny(guard.evaluate(event))

    def test_generic_and_omitted_roles_accept_arbitrary_tasks_with_safe_pins(self):
        self.agent(name='default', filename='default.toml')
        self.agent(name='worker', filename='worker.toml', model='gpt-5.6-terra', model_reasoning_effort='high')
        for name in ['default','worker',None]:
            for task, prompt in [('investigate','Read and explain a bounded issue.'),('repair','Implement the assigned change.')]:
                event = self.event()
                event['tool_input'].update(agent_type=name, task_name=task, message=prompt)
                if name is None:
                    del event['tool_input']['agent_type']
                self.assertEqual(guard.evaluate(event), {})

    def test_only_native_binding_authorizes_profile_and_model(self):
        self.agent(model='gpt-5.6-terra')
        self.agent(name='mapper', filename='unbound-shadow.toml', model='gpt-6-astra', register=False)
        self.assertEqual(guard.evaluate(self.event()), {})
        self.agent(model='gpt-6-astra')
        self.agent(name='mapper', filename='unbound-shadow.toml', register=False)
        self.assertDeny(guard.evaluate(self.event()))
        self.agent(model='gpt-5.6-terra')
        self.policy.write_text('{"allowed_models":["gpt-5.6-luna"]}')
        self.assertDeny(guard.evaluate(self.event()))

    def test_unregistered_cheap_toml_is_denied(self):
        self.agent(name='unbound', filename='unbound.toml', register=False)
        self.agent(name='personal_only', filename='personal.toml', directory=self.personal, register=False)
        for name in ['unbound','personal_only']:
            event = self.event()
            event['tool_input']['agent_type'] = name
            self.assertDeny(guard.evaluate(event))

    def test_native_name_comes_from_bound_file_not_legacy_table_alias(self):
        self.agent(name='implementation_profile', filename='different-file.toml', alias='task_worker', model='gpt-5.6-terra')
        event = self.event()
        event['tool_input']['agent_type'] = 'implementation_profile'
        self.assertEqual(guard.evaluate(event), {})
        event['tool_input']['agent_type'] = 'task_worker'
        self.assertDeny(guard.evaluate(event))

    def test_duplicate_bound_names_with_different_sources_deny(self):
        self.agent(name='mapper', filename='other-mapper.toml', alias='other_binding')
        self.assertDeny(json.loads(self.invoke(json.dumps(self.event()).encode())[1]))

    def test_binding_escape_and_symlink_cannot_move_policy_outside_protection(self):
        external = self.agent(name='external', directory=self.personal, register=False)
        for target in [str(external), '../personal-agents/mapper.toml']:
            self.config.write_text('[agents.mapper]\nconfig_file = ' + json.dumps(target))
            self.assertDeny(json.loads(self.invoke(json.dumps(self.event()).encode())[1]))
        link = self.root / '.codex/agents/escape.toml'
        link.symlink_to(external)
        self.config.write_text('[agents.mapper]\nconfig_file="agents/escape.toml"')
        self.assertDeny(json.loads(self.invoke(json.dumps(self.event()).encode())[1]))
        for controlled in [self.policy, self.flag, self.config]:
            saved = controlled.read_bytes()
            controlled.unlink()
            controlled.symlink_to(external)
            self.assertDeny(json.loads(self.invoke(json.dumps(self.event()).encode())[1]))
            controlled.unlink()
            controlled.write_bytes(saved)

    def test_missing_or_malformed_enabled_policy_denies_and_cannot_enable(self):
        values = [None, 'not JSON', '[]', '{}', '{"allowed_models":[]}',
                  '{"allowed_models":"gpt-5.6-luna"}', '{"allowed_models":[null]}',
                  '{"allowed_models":[["nested"]]}', '{"allowed_models":["*"]}',
                  '{"allowed_models":["gpt-5.6-luna","gpt-5.6-luna"]}',
                  '{"allowed_models":["gpt-5.6-luna"],"exception":true}']
        for value in values:
            with self.subTest(value=value):
                if value is None:
                    self.policy.unlink()
                else:
                    self.policy.write_text(value)
                status, output = self.invoke(json.dumps(self.event()).encode())
                self.assertEqual(status, 0)
                self.assertDeny(json.loads(output))
                guard.set_enabled(False)
                with self.assertRaises((OSError,ValueError)):
                    guard.set_enabled(True)
                self.assertFalse(guard.enabled())
                # Recreate enabled state directly to test the next malformed policy.
                self.flag.write_text('{"enabled":true}')

    def test_legacy_boolean_cannot_authorize_v2_default_inheritance(self):
        event = self.event()
        event['tool_input'].pop('fork_turns')
        event['tool_input']['fork_context'] = False
        self.assertDeny(guard.evaluate(event))

    def test_fresh_context_is_explicit_and_consistent(self):
        for args in [{}, {'fork_turns':'all'}, {'fork_turns':False}, {'fork_turns':0},
                     {'fork_context':0}, {'fork_context':'false'}, {'fork_context':True},
                     {'fork_turns':'none', 'fork_context':True}, {'fork_turns':'all','fork_context':False}]:
            with self.subTest(args=args):
                event = self.event()
                event['tool_input'] = {'agent_type':'mapper', **args}
                self.assertDeny(guard.evaluate(event))

    def test_raw_model_and_effort_fields_denied_even_if_equal_or_null(self):
        for key in ['model', 'reasoning_effort', 'model_reasoning_effort']:
            for value in ['gpt-5.6-luna', 'max', None, '', {'nested':'override'}]:
                with self.subTest(key=key, value=value):
                    self.assertDeny(guard.evaluate(self.event(**{key:value})))

    def test_unregistered_generic_and_invalid_roles_denied(self):
        for name in [None, '', [], {}, 'worker', 'default', '../mapper', ' mapper', 'unknown']:
            with self.subTest(name=name):
                event = self.event()
                event['tool_input']['agent_type'] = name
                self.assertDeny(guard.evaluate(event))

    def test_profiles_need_both_pins_and_required_metadata(self):
        for field in ['model', 'model_reasoning_effort', 'description', 'developer_instructions']:
            for value in [None, '', 1]:
                with self.subTest(field=field, value=value):
                    self.agent(**{field:value})
                    self.assertDeny(guard.evaluate(self.event()))
        self.agent()

    def test_invalid_native_binding_config_or_bound_toml_denies(self):
        file = self.agent()
        for value in ['name = [', 'name="x"\nname="x"']:
            file.write_text(value)
            self.assertDeny(json.loads(self.invoke(json.dumps(self.event()).encode())[1]))
        self.agent()
        for value in ['not TOML [', '', '[agents.mapper]\nconfig_file="agents/missing.toml"',
                      '[agents.mapper]\nconfig_file="agents/mapper.toml"\nconfig_file="agents/mapper.toml"']:
            self.config.write_text(value)
            self.assertDeny(json.loads(self.invoke(json.dumps(self.event()).encode())[1]))

    def test_missing_flag_and_off_are_no_op_even_with_bad_input_or_toml(self):
        self.agent().write_text('broken TOML')
        self.policy.write_text('broken JSON')
        for state in [False, None]:
            if state is False:
                guard.set_enabled(False)
            else:
                self.flag.unlink()
            status, output = self.invoke(b'not JSON')
            self.assertEqual((status, json.loads(output)), (0, {}))

    def test_invalid_flag_fails_as_supported_deny(self):
        for value in ['garbage', '[]', '{}', '{"enabled":"false"}', '{"enabled":0}',
                      '{"enabled":false,"typo":true}']:
            self.flag.write_text(value)
            status, output = self.invoke(json.dumps(self.event()).encode())
            self.assertEqual(status, 0)
            self.assertDeny(json.loads(output))

    def test_input_errors_are_denials_and_do_not_leak_payload(self):
        for raw in [b'', b'not JSON SECRET_FIXTURE', b'[]', b'null', b'{}', b'x' * (guard.LIMIT+1)]:
            status, output = self.invoke(raw)
            self.assertEqual(status, 0)
            self.assertDeny(json.loads(output))
            self.assertNotIn('SECRET_FIXTURE', output)

    def test_unrelated_hooks_do_not_load_profiles(self):
        for event_name, name in [('PreToolUse','Bash'), ('PostToolUse','spawn_agent')]:
            event = {'hook_event_name':event_name, 'tool_name':name}
            with patch.object(guard, 'profiles', side_effect=AssertionError('must not read')):
                self.assertEqual(guard.evaluate(event), {})

    def test_subdirectory_and_wrong_worktree(self):
        nested = self.root / 'nested directory'
        nested.mkdir()
        event = self.event()
        event['cwd'] = str(nested)
        self.assertEqual(guard.evaluate(event), {})
        with tempfile.TemporaryDirectory() as other:
            subprocess.run(['git', 'init', '-q', other], check=True)
            event['cwd'] = other
            self.assertDeny(guard.evaluate(event))

    def test_parser_or_git_failure_emits_deny(self):
        for owner, key in [(guard, 'profiles'), (guard.subprocess, 'run')]:
            with patch.object(owner, key, side_effect=RuntimeError('SECRET_FIXTURE')):
                status, output = self.invoke(json.dumps(self.event()).encode())
                self.assertEqual(status, 0)
                self.assertDeny(json.loads(output))
                self.assertNotIn('SECRET_FIXTURE', output)

    def test_toggle_roundtrip_and_invalid_argument_cannot_enable(self):
        unrelated = self.root / '.codex/other-hook.json'
        unrelated.write_text('untouched')
        original_policy = self.policy.read_bytes()
        for arg, expected in [('--off',False), ('--on',True), ('--off',False)]:
            status, _ = self.invoke(b'', [arg])
            self.assertEqual(status, 0)
            self.assertEqual(guard.enabled(), expected)
            self.assertEqual(unrelated.read_text(), 'untouched')
            self.assertEqual(self.policy.read_bytes(), original_policy)
        self.assertIn('off', self.invoke(b'', ['--status'])[1])

    def test_real_hook_command_from_subdirectory_with_spaces(self):
        dest = self.root / '.agents/system/hooks/delegation_guard.py'
        dest.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE, dest)
        nested = self.root / 'nested directory'
        nested.mkdir()
        config = json.loads((SOURCE.parents[3] / '.codex/hooks.json').read_text())
        hook = config['hooks']['PreToolUse'][0]
        self.assertEqual(hook['matcher'], '^(spawn_agent|Agent|collaborationspawn_agent)$')
        command = hook['hooks'][0]['command']
        for on, override in [(True,False), (True,True), (False,True)]:
            guard.set_enabled(on)
            event = self.event(**({'model':'other'} if override else {}))
            result = subprocess.run(command, shell=True, cwd=nested, input=json.dumps(event),
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            if on and override:
                self.assertDeny(json.loads(result.stdout))
            else:
                self.assertEqual(json.loads(result.stdout), {})


if __name__ == '__main__':
    unittest.main()
