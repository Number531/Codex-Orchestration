# Codex-Orchestration

**Version 0.2.2 · Plugin ID `codex-orchestration` · MIT licensed · Guard off by default**

A small Codex plugin for delegating dynamic tasks through named, model-pinned specialists. It provides three skills, six agent profiles, project guidance, a preview-first installer, and an optional synchronous spawn guard.

For example, a parent can assign repository discovery to `explorer`, implementation to `worker`, and adversarial review to `auditor`. With the guard enabled and active, covered spawns must use a registered role, its configured model and effort, and fresh context. Task names and prompts remain dynamic.

## Requirements

- Python 3.11+ and Git in a Unix environment with `fcntl` and a compatible shell. macOS is the qualified platform. Native Windows Python cannot run this installer; Linux and WSL require their own client validation. Runtime scripts use the standard library; no Python dependency installation is required.
- An existing Git project and permission to review and change its project configuration.
- A compatible Codex client supporting multi-agent V2, the `fork_turns` spawn field, named profiles and synchronous `PreToolUse` denial. The tested engines were CLI `0.154.0` and Desktop bundled engine `0.154.0-alpha.6.2` on macOS. Other versions require validation.
- Access to the configured models through the account/provider used by that client. The bundled Luna/Terra/Sol pins do not grant model access or guarantee prices. Check the [role table and customization guide](docs/configuration.md#bundled-roles) before setup.

The `fork_turns` field and the `collaborationspawn_agent` hook name are compatibility assumptions tested on those engines; this project does not claim they are stable public API contracts. Desktop UI installation/trust, live account access, Windows and other platforms have not been qualified by the original native tests. See [validation and compatibility](docs/validation.md).

## Install the skills

The standalone repository is [Number531/Codex-Orchestration](https://github.com/Number531/Codex-Orchestration), publicly readable. Its catalog is `.agents/plugins/marketplace.json`; the marketplace name is `codex-orchestration`.

```sh
codex plugin marketplace add https://github.com/Number531/Codex-Orchestration.git
codex plugin list --available --json --marketplace codex-orchestration
codex plugin add codex-orchestration@codex-orchestration
```

No repository invitation is required for HTTPS access. Use the SSH equivalent if that is how you authenticate. Plugin installation makes the skills available; project setup is a separate step. The package includes its [MIT License](LICENSE).

## Set up one project

Choose one of the following routes. Both target one existing Git worktree and leave the delegation guard off.

### Installed-plugin route

1. Open your target Git project in a new Codex session after installing the plugin.
2. Select `orchestration-setup` from the skill picker and ask: “Preview Codex Orchestration setup for this project. Leave enforcement off.” The skill locates its own installed package; no shell variable or second clone is needed.
3. Review the planned files and any conflicts. If the preview is correct, ask the skill to apply it to that project. Do not force an overwrite.
4. Continue with [review and trust](#review-and-trust).

### Checkout route

Use this route when you want project configuration without registering the plugin skills. Clone a reviewed checkout, then replace `/absolute/path/to/project` with the existing Git worktree root you want to configure:

```sh
git clone https://github.com/Number531/Codex-Orchestration.git
cd Codex-Orchestration
ORCHESTRATION_PACKAGE="$PWD/plugins/codex-orchestration"
ORCHESTRATION_PROJECT="/absolute/path/to/project"
python3 "$ORCHESTRATION_PACKAGE/scripts/setup.py" --project "$ORCHESTRATION_PROJECT"
```

The default is a read-only preview. It prints the planned paths or `Preview: no changes.` Review the source assets and existing project configuration before applying. In the same shell:

```sh
python3 "$ORCHESTRATION_PACKAGE/scripts/setup.py" --project "$ORCHESTRATION_PROJECT" --apply
```

A separate disposable Git project is a useful first trial; the [validation guide](docs/validation.md#try-the-documented-setup-safely) gives complete commands.

### Review and trust

Review the resulting project diff before using the installed configuration. Two separate trust decisions matter:

1. Open Codex in the target project and complete its project-trust prompt after reviewing the project. Project `.codex` settings and hooks load only from a trusted project.
2. In the CLI, open `/hooks`, locate the project hook from `.codex/hooks.json`, and review its command and current definition before trusting it. New or changed non-managed hooks require review again. This trust decision does not turn on delegation enforcement.

Start a fresh session after profile/config changes. Check the flag from the configured project:

```sh
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --status
```

A new setup should print `Delegation guard: off`. OpenAI documents the [hook review flow](https://learn.chatgpt.com/docs/hooks); Desktop UI qualification is recorded separately in the [compatibility guide](docs/validation.md). Setup never grants trust automatically.

New installations leave the guard off. Reruns preserve valid existing flag and model-policy values. A setup conflict stops the operation; use [operations and recovery](docs/operations.md) rather than forcing an overwrite.

Upgrading from `0.1.0` changes the plugin/skill identifiers and managed guidance markers. Follow the [manual migration guide](docs/operations.md#migrate-from-010) before setup; the installer refuses recognized legacy guidance or a legacy setup lock instead of appending a second managed block.

## Turn enforcement on or off

Leave enforcement off during ordinary onboarding. Enable it only when a demonstrated delegation-policy issue calls for enforcement and the user authorizes the policy. Turning it on does not fix installation, interpreter, or trust errors.

To enable enforcement in the configured project:

```sh
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --on
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --status
```

To disable it:

```sh
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --off
```

`--status` reports `Delegation guard: on` or `Delegation guard: off`. **It reports the flag, not proof that Codex loaded or trusted the hook.** The flag is read on each covered spawn. Turning it off leaves the configured agent profiles and default child model in place. There is no global toggle in this package. Disabling/uninstalling the plugin does not remove project assets or switch their guard off.

## Use the skills

| Skill | Example request | Behavior |
|---|---|---|
| `orchestration-setup` | “Preview Codex Orchestration setup for this project.” | Inspects project settings and previews explicit installation. |
| `orchestration-delivery` | “Implement this bounded fix with a short plan, targeted tests and independent verification.” | Uses the existing project workflow where one owns the task; otherwise provides a small delivery process. |
| `orchestration-review` | “Verify this change against its acceptance criteria.” | Selects a focused audit or verification role and reports evidence and limits. |

These skills do not authorize spending, remote writes, merges, or policy changes outside the user's task. They also do not replace project-specific instructions. The setup procedure installs a concise managed [AGENTS section](assets/AGENTS.md), not the original development repository's full workflow system.

## Learn more

- [Configuration](docs/configuration.md): installed files, role pins, dynamic tasks, custom models/agents and enforcement limits.
- [Operations and recovery](docs/operations.md): conflicts, upgrades, cleanup and troubleshooting.
- [Validation and compatibility](docs/validation.md): reproducible checks, evidence and unverified surfaces.
- [Changelog](CHANGELOG.md), [contribution guidance](../../CONTRIBUTING.md), and [security policy](../../SECURITY.md).

The package is available under the [MIT License](LICENSE), including commercial and enterprise use. Preserve its copyright and permission notices when redistributing copies or substantial portions, including setup-generated project assets. Setup does not change your project's own license; include this notice with any redistributed package assets.
