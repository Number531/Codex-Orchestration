# Aperture-Agent-System

**Version 0.1.0 · Plugin ID `aperture-agent-system` · Guard off by default**

A small Codex plugin for delegating dynamic tasks through named, model-pinned specialists. It provides three skills, six agent profiles, project guidance, a preview-first installer, and an optional synchronous spawn guard.

For example, a parent can assign repository discovery to `explorer`, implementation to `worker`, and adversarial review to `auditor`. With the guard enabled and active, covered spawns must use a registered role, its configured model and effort, and fresh context. Task names and prompts remain dynamic.

## Requirements

- Python 3.11+ and Git on the machine where project setup and hooks run. Runtime scripts use the standard library; no Python dependency installation is required.
- An existing Git project and permission to review and change its project configuration.
- A compatible Codex client supporting multi-agent V2, the `fork_turns` spawn field, named profiles and synchronous `PreToolUse` denial. The tested engines were CLI `0.154.0` and Desktop bundled engine `0.154.0-alpha.6.2` on macOS. Other versions require validation.
- Access to the configured models through the account/provider used by that client. The bundled Luna/Terra/Sol pins do not grant model access or guarantee prices. Check the [role table and customization guide](docs/configuration.md#bundled-roles) before setup.

The `fork_turns` field and the `collaborationspawn_agent` hook name are compatibility assumptions tested on those engines; this project does not claim they are stable public API contracts. Desktop UI installation/trust, live account access, Windows and other platforms have not been qualified by the original native tests. See [validation and compatibility](docs/validation.md).

## Install the skills

The standalone repository is [Number531/Codex-Orchestration](https://github.com/Number531/Codex-Orchestration), initially private. Its catalog is `.agents/plugins/marketplace.json`; the marketplace name is `codex-orchestration`.

```sh
codex plugin marketplace add https://github.com/Number531/Codex-Orchestration.git
codex plugin list --available --json --marketplace codex-orchestration
codex plugin add aperture-agent-system@codex-orchestration
```

Private access requires your GitHub credentials. Use the SSH equivalent if that is how you authenticate. In a new Codex session, select the installed `aperture-setup` skill for your target project. Installation alone does **not** register project agents, trust hooks, or enable the guard.

Alternatively, clone a reviewed checkout and use its setup script directly. This installs the project assets without registering plugin skills:

```sh
git clone https://github.com/Number531/Codex-Orchestration.git
cd Codex-Orchestration
APERTURE_PACKAGE="$PWD/plugins/aperture-agent-system"
```

## Set up one project

Use the absolute root of the target Git worktree, not a subdirectory. A separate disposable Git project is a useful first trial.

```sh
python3 "$APERTURE_PACKAGE/scripts/setup.py" --project /absolute/path/to/project
```

The default is a read-only preview. It prints the planned paths or `Preview: no changes.` Review the source assets and the target project's existing configuration before applying the plan:

```sh
python3 "$APERTURE_PACKAGE/scripts/setup.py" --project /absolute/path/to/project --apply
```

Review the resulting project diff, complete the client's normal project/hook trust flow, and start a fresh session. Setup does not grant that trust. If you installed through the plugin manager, `aperture-setup` resolves its package location; the shell variable above is only for the checkout route.

New installations leave the guard off. Reruns preserve valid existing flag and model-policy values. A setup conflict stops the operation; use [operations and recovery](docs/operations.md) rather than forcing an overwrite.

## Turn enforcement on or off

In the configured project, after reviewing and authorizing the policy:

```sh
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --on
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --status
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --off
```

`--status` reports `Delegation guard: on` or `Delegation guard: off`. **It reports the flag, not proof that Codex loaded or trusted the hook.** The flag is read on each covered spawn. Turning it off leaves the configured agent profiles and default child model in place. There is no global toggle in this package. Disabling/uninstalling the plugin does not remove project assets or switch their guard off.

## Use the skills

| Skill | Example request | Behavior |
|---|---|---|
| `aperture-setup` | “Preview Aperture setup for this project.” | Inspects project settings and previews explicit installation. |
| `aperture-delivery` | “Implement this bounded fix with a short plan, targeted tests and independent verification.” | Uses the existing project workflow where one owns the task; otherwise provides a small delivery process. |
| `aperture-review` | “Verify this change against its acceptance criteria.” | Selects a focused audit or verification role and reports evidence and limits. |

These skills do not authorize spending, remote writes, merges, or policy changes outside the user's task. They also do not replace project-specific instructions. The setup procedure installs a concise managed [AGENTS section](assets/AGENTS.md), not the original development repository's full workflow system.

## Learn more

- [Configuration](docs/configuration.md): installed files, role pins, dynamic tasks, custom models/agents and enforcement limits.
- [Operations and recovery](docs/operations.md): conflicts, upgrades, cleanup and troubleshooting.
- [Validation and compatibility](docs/validation.md): reproducible checks, evidence and unverified surfaces.
- [Changelog](CHANGELOG.md), [contribution guidance](../../CONTRIBUTING.md), and [security policy](../../SECURITY.md).

The package has no declared distribution license yet. Keeping the repository private does not settle the licensing decision for a future public release.
