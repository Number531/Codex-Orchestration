# Validation and compatibility

[Back to the quick start](../README.md)

## Evidence boundaries

| Surface | Evidence | Limit |
|---|---|---|
| Setup, guard, profiles, package and documentation contracts | 54 deterministic unit tests passed for the `0.2.2` candidate, including MIT metadata/license-copy consistency, legacy migration refusal, installer lock exclusion and documentation-check regressions. | Synthetic projects do not establish live account access or UI behavior. |
| Native spawn behavior | 17 cases passed on CLI `0.154.0` and Desktop engine `0.154.0-alpha.6.2` on macOS, recorded 2026-09-12. | The harness supplies reviewed configuration/trust overrides and a loopback scripted provider. |
| Local-catalog installation and setup | CLI `0.154.0` and Desktop engine `0.154.0-alpha.6.2` installed the `0.2.1` candidate on macOS, recorded 2026-09-12. | This is a local-catalog trial; it does not establish GitHub authentication or Desktop UI behavior. |
| Pinned GitHub-commit installation | Both engines installed commit `1ea514efdacb8aa1077e4eb81a8f7d90d1255306` through the GitHub catalog on 2026-09-13. | Used the maintainer's existing Git authentication while the repository was private; no separate community-account trial. |
| MIT package installation | Both engines installed `0.2.2` from a local catalog on 2026-09-13. The cache included the MIT notice and metadata; all 31 package files matched the trial checkout, setup was repeatable, and the guard stayed off. | Disposable configuration/cache and projects only; no trust grant, Desktop UI test or live-model call. |
| Desktop UI install/trust and live models | Not established by those tests. | Requires a separately authorized onboarding trial. |
| Windows, other clients or versions | Not qualified by the original native matrix. | The installer uses POSIX `fcntl`; the hook command assumes a compatible shell. |

The `0.2.0` branding update preserves the guard, six role profiles, model pins and default-off flag. It renames package/skill identifiers and installer markers, and adds refusal checks for recognized legacy guidance/locks. Local setup tests cover that transition. Do not treat inherited native evidence as a newly executed matrix or a test of the renamed plugin's UI installation.

The `0.2.1` trial used a separate temporary Codex configuration/cache and Git project for each executable. Fresh processes listed the installed, enabled plugin; its three skill files and all 30 package files matched the candidate checkout. Setup ran from the installed cache, a second preview reported no changes, and the flag reported off. No auth files were copied, trust granted or live models called. The real global configuration and plugin-registry hashes were unchanged. Codex still discovered the ambient personal marketplace; the test selected only this package and is not a claim of complete operating-system isolation.

The subsequent pinned GitHub-commit trial repeated those checks successfully on both engines against the exact commit above. Later public-state documentation edits did not change runtime assets. After the visibility change, unauthenticated HTTP requests separately confirmed public repository and Issues access. That access check did not invoke Codex or establish model availability.

The `0.2.2` licensing update preserves those runtime assets and adds the package's MIT notice. The separate local-catalog trial confirmed that the licensed package reached each cache and that real global configuration hashes were unchanged. Versioned-package installation and project-asset installation remain separate; see [operations](operations.md#upgrade-a-project).

The production Desktop app was not launched for the trial. A safe, documented separate UI profile was not established for that build; qualifying its graphical installation and normal trust flow requires a disposable OS user/VM or a supported isolated app environment.

## Local checks

From the repository root, with Python 3.11+ and Git:

```sh
python3 -B -m unittest discover -s plugins/codex-orchestration/test -p 'test_*.py'
python3 -B plugins/codex-orchestration/test/check_catalog.py
python3 -B plugins/codex-orchestration/test/check_docs.py
```

Tests cover setup preservation/conflicts, filesystem failures, rollback behavior, guard acceptance/denial, role pins, manifests, synthetic catalogs and documentation-check failures. The catalog check verifies this repository's single-plugin catalog. The offline documentation check validates tracked Markdown inline local links, ATX heading anchors and JSON/TOML fences; it does not execute shell examples or check external URLs. They do not install into real projects or global Codex configuration.

## Try the documented setup safely

This manual exercise creates a temporary project and invokes no model. Run from the repository root:

```sh
ORCHESTRATION_PACKAGE="$PWD/plugins/codex-orchestration"
ORCHESTRATION_TRIAL="$(mktemp -d)"
git init -q "$ORCHESTRATION_TRIAL"
python3 "$ORCHESTRATION_PACKAGE/scripts/setup.py" --project "$ORCHESTRATION_TRIAL"
python3 "$ORCHESTRATION_PACKAGE/scripts/setup.py" --project "$ORCHESTRATION_TRIAL" --apply
python3 "$ORCHESTRATION_PACKAGE/scripts/setup.py" --project "$ORCHESTRATION_TRIAL"
python3 "$ORCHESTRATION_TRIAL/.agents/system/hooks/delegation_guard.py" --status
```

After apply, the next preview should report `Preview: no changes.` and status should be off. Inspect the temporary project before removing it yourself. This checks setup, not native enforcement.

## Native engine matrix

The opt-in harness needs Node.js, Python 3.11+, Git, a compatible local Codex executable and an existing local model catalog. Supply the absolute executable path:

```sh
node plugins/codex-orchestration/test/native-smoke.mjs /absolute/path/to/codex
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
