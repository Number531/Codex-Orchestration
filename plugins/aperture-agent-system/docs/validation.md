# Validation and compatibility

[Back to the quick start](../README.md)

## Evidence boundaries

| Surface | Evidence | Limit |
|---|---|---|
| Setup, guard, profiles and package contracts | 45 deterministic unit tests passed for the original package. | Synthetic projects do not establish live account access or UI behavior. |
| Native spawn behavior | 17 cases passed on CLI `0.154.0` and Desktop engine `0.154.0-alpha.6.2` on macOS, recorded 2026-09-12. | The harness supplies reviewed configuration/trust overrides and a loopback scripted provider. |
| Catalog discovery | Both original tested binaries discovered the original entry without installation. | Standalone catalog identity and consistency are checked separately. |
| Desktop UI install/trust and live models | Not established by those tests. | Requires a separately authorized onboarding trial. |
| Windows, other clients or versions | Not qualified by the original native matrix. | The installer uses POSIX `fcntl`; the hook command assumes a compatible shell. |

The standalone extraction retains the original runtime assets and default-off flag. Repository metadata, catalog identity, documentation and catalog tests are adapted for `Codex-Orchestration`. Do not treat inherited native evidence as a newly executed matrix.

## Local checks

From the repository root, with Python 3.11+ and Git:

```sh
python3 -B -m unittest discover -s plugins/aperture-agent-system/test -p 'test_*.py'
python3 -B plugins/aperture-agent-system/test/check_catalog.py
```

Tests cover setup preservation/conflicts, filesystem failures, rollback behavior, guard acceptance/denial, role pins, manifests and synthetic catalogs. The catalog check verifies this repository's single-plugin catalog. They do not install into real projects or global Codex configuration.

## Try the documented setup safely

This manual exercise creates a temporary project and invokes no model. Run from the repository root:

```sh
APERTURE_PACKAGE="$PWD/plugins/aperture-agent-system"
APERTURE_TRIAL="$(mktemp -d)"
git init -q "$APERTURE_TRIAL"
python3 "$APERTURE_PACKAGE/scripts/setup.py" --project "$APERTURE_TRIAL"
python3 "$APERTURE_PACKAGE/scripts/setup.py" --project "$APERTURE_TRIAL" --apply
python3 "$APERTURE_PACKAGE/scripts/setup.py" --project "$APERTURE_TRIAL"
python3 "$APERTURE_TRIAL/.agents/system/hooks/delegation_guard.py" --status
```

After apply, the next preview should report `Preview: no changes.` and status should be off. Inspect the temporary project before removing it yourself. This checks setup, not native enforcement.

## Native engine matrix

The opt-in harness needs Node.js, Python 3.11+, Git, a compatible local Codex executable and an existing local model catalog. Supply the absolute executable path:

```sh
node plugins/aperture-agent-system/test/native-smoke.mjs /absolute/path/to/codex
```

It creates a temporary Git project and installs there. It reads `models_cache.json` from `CODEX_HOME` or `~/.codex`, selecting Luna, Terra, Sol and Astra entries for the cases. It does not read auth files, upload source, call paid models or modify global configuration. Successful V2 cases create normal synthetic local session records; their IDs are reported with bounded evidence.

Preflight stops if the effective Codex directory contains `hooks.json`, or if `/etc/codex/hooks.json`, `/etc/codex/requirements.toml` or `/etc/codex/config.toml` exists. These sources need separate review; do not remove real security configuration to make a test pass. Temporary project files may already exist when preflight stops.

The 17 cases cover Luna/Terra/Sol admission, default/dynamic tasks, unregistered and costly custom roles, native names versus aliases, inline overrides, inherited context, retry with Terra, off-mode Astra, and effective protected-directory sandbox behavior. Each result establishes only the condition it exercises.

## Validate a real client

Before adopting a new client or model configuration, use a disposable project and an authorized account. Record package, OS and exact client/engine versions, requested/effective sandbox, hook/trust state and observed child model/effort. Exercise allowed roles, a policy-denied role, inline override denial and both toggle states. Distinguish a pre-spawn denial from a provider rejecting a model later.

Live checks may incur normal account usage and need explicit task authorization. For Desktop, separately verify discovery, installation, project setup and normal trust. The engine-only matrix does not test that UI flow.

## Source references

- [Plugin packaging and repository catalogs](https://developers.openai.com/plugins/build/plugins) establish the distribution structure; installation and public directory submission are separate.
- [Native agent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents) explains project/personal roles. This guard requires protected project bindings.
- [Hooks](https://learn.chatgpt.com/docs/hooks) explains synchronous decisions and coverage limits. Hooks are one guardrail, not an account-wide boundary.
- [Model availability](https://learn.chatgpt.com/docs/enterprise/workspace-model-availability) depends on identity, client and product surface.

Public documentation was reviewed on 2026-09-12. It did not establish a stable public contract for `fork_turns` or the observed `collaborationspawn_agent` spelling. Keep those assumptions in the compatibility matrix and revalidate when Codex changes.
