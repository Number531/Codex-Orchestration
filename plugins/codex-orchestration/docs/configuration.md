# Configuration

[Back to the quick start](../README.md)

## Installed project files

Setup operates on one Git worktree. Paths below are relative to that worktree root.

| Path | Purpose | Rerun behavior |
|---|---|---|
| `AGENTS.md` | Managed guidance between `codex-orchestration:begin/end` markers | Preserves surrounding text; an edited managed block conflicts. |
| `.codex/config.toml` | Features, default child settings and six role bindings | Adds missing compatible settings; conflicting values or unsupported TOML layouts require manual integration. |
| `.codex/agents/{default,explorer,worker,implementer,auditor,verifier}.toml` | Model/effort pins, sandbox defaults and instructions | Equal files are unchanged; edited package-owned profiles conflict. |
| `.codex/hooks.json` | One synchronous spawn hook | Preserves unrelated hooks; ambiguous or modified copies of this guard conflict. |
| `.codex/delegation-policy.json` | Exact allowed child-model IDs | Preserves an existing valid policy. |
| `.codex/delegation-guard.json` | Per-project enforcement flag | Installs `false` initially; preserves an existing valid flag. |
| `.agents/system/hooks/delegation_guard.py` | Local guard and toggle CLI | Equal file is unchanged; edited owned file conflicts. |

The installer does not edit `~/.codex`, grant trust, or configure every worktree automatically. The guard and its session must resolve to the same Git worktree root.

## Bundled roles

| Role | Model | Reasoning effort | Requested sandbox |
|---|---|---|---|
| `default` | `gpt-5.6-luna` | `max` | Read only |
| `explorer` | `gpt-5.6-luna` | `max` | Read only |
| `worker` | `gpt-5.6-terra` | `high` | Workspace write |
| `implementer` | `gpt-5.6-terra` | `high` | Workspace write |
| `auditor` | `gpt-5.6-sol` | `high` | Read only |
| `verifier` | `gpt-5.6-terra` | `medium` | Read only |

The shared default child model is Luna with `max` effort. The package does not set the parent model; Astra can remain the parent while selecting among these roles. Sol is allowed. This is an explicit model allowlist, not a price calculator, spending cap, or automatic cheapest-model selector.

Confirm the exact IDs and effort values work in your Codex account/client. An API model listing alone does not prove access on every Codex surface. See [OpenAI's model-availability guidance](https://learn.chatgpt.com/docs/enterprise/workspace-model-availability).

Sandbox modes are requested settings, subject to effective client policy. All bundled instructions forbid further delegation, but `agents.max_depth=1` is not claimed to enforce nesting under V2.

## Flag and model pool

The initial flag is:

```json
{
  "enabled": false
}
```

The initial policy is:

```json
{
  "allowed_models": ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]
}
```

Use the [toggle commands](../README.md#turn-enforcement-on-or-off) to change the flag. The policy accepts 1–32 unique exact IDs made of lowercase letters, digits, periods and hyphens, starting with a letter or digit. Provider-qualified IDs containing `/`, `:` or `_` do not fit this release's policy schema.

`--on` checks policy and registration structure. It does not contact a provider, prove account access, or establish that the client has loaded the hook. Invalid policy/configuration can make it fail. A successful toggle still requires an actual compatible, trusted client to enforce spawns.

## Dynamic tasks and enforcement

The parent can choose a fresh task name, prompt and suitable registered role for each delegation. On the tested schema, a covered request uses `fork_turns="none"` and omits inline model/effort overrides. A missing `agent_type` is evaluated as `default`.

When enabled and loaded, the hook checks:

1. The event is a covered `PreToolUse` spawn and the session belongs to this worktree.
2. The role has a supported project `config_file` binding and a valid native profile name.
3. The profile supplies non-empty strings for `model`, `model_reasoning_effort`, `description` and `developer_instructions`.
4. The selected model is in `allowed_models`.
5. The call contains no model/effort overrides and explicitly requests fresh context with the supported `fork_turns` field.

A denied role is not silently rewritten. The parent may select another suitable registered role. An exception requires a separately reviewed policy/profile change or disabling the guard; a prompt claiming “user approved” is not an override. Astra children are outside the initial pool.

## Add a custom role

Make reviewed project edits after setup. For example, create `.codex/agents/researcher.toml`:

```toml
name = "researcher"
description = "Read-only evidence collection for a bounded question."
model = "gpt-5.6-luna"
model_reasoning_effort = "max"
sandbox_mode = "read-only"
developer_instructions = "Read only the assigned sources. Cite evidence and report uncertainty. Do not create subagents or create, resume or update goals. Do not expand the user's authorization."
```

Add a unique binding to the project's `.codex/config.toml`:

```toml
[agents.researcher]
description = "Read-only evidence collection for a bounded question."
config_file = "agents/researcher.toml"
```

Do not duplicate an existing TOML table. The path resolves from `.codex/config.toml`; the bound file must remain under protected `.codex/agents/` and end in `.toml`. Names must match `[a-z][a-z0-9_-]*`. The guard uses the bound TOML's `name`, not a legacy table alias; keeping them equal avoids ambiguity. Distinct files may not claim the same native name.

Restart the Codex session after profile/config changes. Creating a TOML without native registration is insufficient for this guard. This example reuses an allowed model; changing it requires a compatible policy entry and account access.

## Use different models

If the bundled models are unavailable, review a compatible alternative before delegating. Update each affected project profile's model/effort, shared defaults in `.codex/config.toml` when appropriate, and `.codex/delegation-policy.json`. Keep sandbox and task restrictions appropriate to the role. Validate the combination in a disposable project before relying on it.

Customizing package-owned profiles intentionally makes later setup previews report a conflict. Preserve customizations and merge future package changes manually; this release has no force-update or model-migration command. The original native matrix does not validate a new provider or model combination.

## What the guard does not cover

The matcher covers `spawn_agent`, `Agent` and the observed `collaborationspawn_agent` name. Other paths, tool names, direct API calls and independent clients are not an account-wide enforcement boundary. The handler emits valid denial JSON for errors it catches; a missing interpreter, unloaded hook, host timeout or client behavior still needs validation. It does not override normal permission handling or return blanket approval.

OpenAI documents hooks as a guardrail with paths that may opt out; see [Hooks](https://learn.chatgpt.com/docs/hooks). [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) describes native agents. This package adds stricter local registration/spawn requirements; its [compatibility evidence](validation.md) defines the tested scope.
