#!/usr/bin/env python3
"""Optional, synchronous Codex spawn guard. Python 3.11+; no network calls."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
FLAG = ROOT / '.codex/delegation-guard.json'
POLICY = ROOT / '.codex/delegation-policy.json'
CONFIG = ROOT / '.codex/config.toml'
LIMIT = 1024 * 1024


def read_bounded(path):
    with path.open('rb') as handle:
        data = handle.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise ValueError('configuration exceeds 1 MiB')
    return data.decode('utf-8')


def enabled():
    if FLAG.is_symlink() or FLAG.resolve().parent != ROOT / '.codex':
        raise ValueError('flag must be a regular project-local file')
    if not FLAG.exists():
        return False
    value = json.loads(read_bounded(FLAG))
    if not isinstance(value, dict) or set(value) != {'enabled'} or type(value['enabled']) is not bool:
        raise ValueError('delegation-guard.json must contain only an enabled boolean')
    return value['enabled']


def profiles():
    import tomllib
    if CONFIG.is_symlink() or CONFIG.resolve().parent != ROOT / '.codex':
        raise ValueError('agent configuration must be project-local')
    agents = tomllib.loads(read_bounded(CONFIG)).get('agents')
    if not isinstance(agents, dict) or len(agents) > 128:
        raise ValueError('expected a bounded native agents configuration')
    result = {}
    sources = {}
    # The runtime binding, not a directory inventory, chooses the profile.
    # Keep bound files under Codex's protected project directory.
    for role, registration in agents.items():
        if not isinstance(registration, dict):
            continue
        relative = registration.get('config_file')
        if (not re.fullmatch(r'[a-z][a-z0-9_-]*', role) or not isinstance(relative, str)
                or Path(relative).is_absolute()):
            raise ValueError('expected a native role with a relative config_file')
        file = (ROOT / '.codex' / relative).resolve()
        if file.suffix != '.toml' or not file.is_relative_to(ROOT / '.codex/agents'):
            raise ValueError('bound profile must remain in protected project agents')
        value = tomllib.loads(read_bounded(file))
        name = value.get('name')
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', name):
            raise ValueError('bound agent profile has an invalid name')
        if name in sources and sources[name] != file:
            raise ValueError('ambiguous native name across bound profile files')
        sources[name] = file
        # V2 exposes the bound TOML's name, not the legacy agents table alias.
        result[name] = value
    return result


def allowed_models():
    if POLICY.is_symlink() or POLICY.resolve().parent != ROOT / '.codex':
        raise ValueError('cost policy must be a regular project-local file')
    value = json.loads(read_bounded(POLICY))
    if not isinstance(value, dict) or set(value) != {'allowed_models'}:
        raise ValueError('policy must contain only allowed_models')
    models = value['allowed_models']
    if (not isinstance(models, list) or not 1 <= len(models) <= 32
            or any(not isinstance(model, str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', model)
                   for model in models) or len(set(models)) != len(models)):
        raise ValueError('allowed_models must be a nonempty unique list of exact model IDs')
    return frozenset(models)


def deny(reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': 'Delegation guard: ' + reason}}


def evaluate(event):
    if not isinstance(event, dict):
        return deny('expected a hook event object.')
    if not isinstance(event.get('hook_event_name'), str) or not isinstance(event.get('tool_name'), str):
        return deny('missing hook event or tool name.')
    if event.get('hook_event_name') != 'PreToolUse' or event.get('tool_name') not in (
            'spawn_agent', 'Agent', 'collaborationspawn_agent'):
        return {}
    cwd = event.get('cwd')
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return deny('missing absolute session cwd.')
    git_root = subprocess.run(['git', '-C', cwd, 'rev-parse', '--show-toplevel'],
                              capture_output=True, text=True, timeout=1, check=True).stdout.strip()
    if Path(git_root).resolve() != ROOT:
        return deny('hook and session must belong to the same worktree.')
    args = event.get('tool_input')
    if not isinstance(args, dict):
        return deny('expected spawn arguments as an object.')
    name = args.get('agent_type', 'default')
    if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_-]*', name):
        return deny('select a registered named agent_type.')
    profile = profiles().get(name)
    if profile is None:
        return deny('agent_type has no supported project config_file binding. '
                    'Use a configured default/worker role; creating a TOML alone does not register it.')
    for field in ('model', 'model_reasoning_effort', 'description', 'developer_instructions'):
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            return deny('selected profile must specify model, effort, description and instructions.')
    if profile['model'] not in allowed_models():
        return deny('selected profile model is outside the approved child-model pool. '
                    'Select a profile in delegation-policy.json allowed_models, or request a '
                    'user-reviewed policy change. A custom profile does not grant an exception.')
    if any(field in args for field in ('model', 'reasoning_effort', 'model_reasoning_effort')):
        return deny('omit model and effort overrides; the named profile supplies both. '
                    'A user-authorized exception requires a separate reviewed policy change.')
    # This pilot targets the observed V2 schema. A legacy/unknown field must not
    # authorize a spawn whose real fork_turns would default to "all".
    if args.get('fork_turns') != 'none' or 'fork_context' in args:
        return deny('request fork_turns="none" using the supported multi-agent V2 client.')
    # No "allow" override: keep normal permission handling and other hooks intact.
    return {}


def set_enabled(value):
    if FLAG.is_symlink() or FLAG.resolve().parent != ROOT / '.codex':
        raise ValueError('refusing to replace a symlink flag file')
    if value:
        allowed_models()
        if not profiles():
            raise ValueError('no registered agent profiles')
    FLAG.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=FLAG.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({'enabled': value}, handle, indent=2)
            handle.write('\n')
        os.replace(temporary, FLAG)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--on', action='store_true')
    mode.add_argument('--off', action='store_true')
    mode.add_argument('--status', action='store_true')
    args = parser.parse_args()
    if args.on or args.off or args.status:
        try:
            if args.on or args.off:
                set_enabled(args.on)
            print('Delegation guard: ' + ('on' if enabled() else 'off'))
            return 0
        except Exception:
            print('Cannot read/update delegation guard; check flag/policy JSON and agent TOMLs '
                  'with Python 3.11+.', file=sys.stderr)
            return 1
    try:
        if not enabled():
            result = {}
        else:
            raw = sys.stdin.buffer.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError('hook input too large')
            result = evaluate(json.loads(raw))
    except Exception:
        # A crash or invalid stdout may fail open in Codex; emit a valid deny instead.
        # Do not echo input, prompts, paths or TOML contents into diagnostics.
        result = deny('invalid input or unavailable policy. Check Python 3.11+, '
                      'flag/policy JSON, agent TOMLs and session worktree. Retry after correction.')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
