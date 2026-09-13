"""Check native team catalog integration; uses no network or global config."""
import json
from pathlib import Path


def check(root):
    root = Path(root).resolve()
    package = root / 'plugins/codex-orchestration'
    manifest = json.loads((package / 'plugin.json').read_text())
    compat = json.loads((package / '.codex-plugin/plugin.json').read_text())
    catalog = json.loads((root / '.agents/plugins/marketplace.json').read_text())
    assert catalog['name'] == 'codex-orchestration'
    names = [entry['name'] for entry in catalog['plugins']]
    assert names == [manifest['name']], 'Catalog must contain only the Codex Orchestration package'
    entry = next(entry for entry in catalog['plugins'] if entry['name'] == manifest['name'])
    assert entry['source'] == {'source': 'local', 'path': './plugins/codex-orchestration'}
    assert entry['policy']['installation'] == 'AVAILABLE'
    assert entry['policy']['authentication'] == 'ON_INSTALL'
    assert entry['category'] == 'Productivity'
    assert compat['name'] == manifest['name'] == 'codex-orchestration'
    assert compat['version'] == manifest['version'] == entry['version']
    assert compat['repository'] == manifest['repository'] == 'https://github.com/Number531/Codex-Orchestration'
    assert (root / entry['source']['path']).resolve() == package
    assert len(list((package / 'skills').glob('*/SKILL.md'))) == 3


if __name__ == '__main__':
    check(Path(__file__).resolve().parents[3])
    print('PASS: native catalog resolves to the version-consistent portable core package.')
