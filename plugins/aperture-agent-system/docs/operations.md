# Operations and recovery

[Back to the quick start](../README.md)

## Inspect the current state

```sh
python3 /absolute/path/to/project/.agents/system/hooks/delegation_guard.py --status
```

Inspect the project's config, agent TOMLs, hooks and model-policy JSON, plus the client's loaded configuration and trust state. A status of `on` only proves the flag is true. Restart after profile/config edits; the flag itself is reread on each covered spawn.

## Setup conflicts

The installer preflights its complete planned write set. It preserves unrelated guidance, compatible configuration and unrelated hooks. It does not rewrite arbitrary TOML or overwrite edited package-owned assets.

| Symptom | Meaning and action |
|---|---|
| `--project must...Git root` | Use the absolute existing Git worktree root, not a subdirectory. |
| Conflicting required TOML value/table | Review the existing and package settings and integrate the intended values manually. |
| Unsupported TOML layout | The bounded merger cannot prove preservation; manually integrate required settings. |
| Conflicting owned file / changed managed AGENTS block | Compare the customized profile, script or guidance with the package and preserve intentional edits. |
| Ambiguous or changed guard hook | Review the exact hook entries without removing unrelated hooks. |
| Symlink, malformed file, or size-bound refusal | Correct the specific file/path. Files and planned outputs are bounded to 1 MiB. |

Preview again after correction. Equal files are no-ops; valid existing guard/policy values are preserved.

## Upgrade a project

The plugin package/cache and each project's installed files are independent layers:

1. Review the [changelog](../CHANGELOG.md) and compatibility notes.
2. Obtain a reviewed new checkout, or refresh the catalog with `codex plugin marketplace upgrade codex-orchestration` and use the client's supported package update flow. A catalog refresh is not proof the installed cache changed; check the installed version.
3. Run the new package's setup preview against each target worktree.
4. Integrate intended changes through reviewed edits, preserving custom roles, policies, flags and unrelated files. Apply only a clean, understood plan.
5. Review the diff, complete any required trust review, restart affected sessions and rerun relevant validation.

Setup does not automatically upgrade customized assets. Plugin disablement, reinstallation and catalog refresh do not synchronize or remove project configuration.

If you previously installed this plugin from another catalog, inspect the installed source and avoid enabling duplicate copies. The standalone selector is `aperture-agent-system@codex-orchestration`. Use the client's normal plugin management to retire the old copy when appropriate; do not remove other plugins or their catalog as a side effect. Existing project markers and role IDs are unchanged, so review their state before reapplying setup.

## Recover an interrupted setup

Setup rechecks originals, serializes cooperating setup processes with `.aperture-agent-system.setup.lock`, and replaces each file atomically. A caught failure attempts to restore its own unchanged writes. Abrupt termination or unrelated concurrent editing can still leave a partial multi-file installation.

Inspect the project diff after a crash. If the lock remains, confirm no setup process is running before removing that one stale lock. Avoid editing targets during apply. Re-run preview and reconcile partial changes before applying again; do not discard unrelated work with blanket cleanup commands.

## Diagnose a denied or unenforced spawn

| Symptom | Check |
|---|---|
| No supported role binding | Confirm `[agents.<role>].config_file`, protected profile path and native `name`; restart after registration changes. |
| Missing profile fields | Supply non-empty `model`, `model_reasoning_effort`, `description` and `developer_instructions`. |
| Model outside approved pool | Choose a suitable registered role or review the actual policy/profile change. Sol is already allowed. |
| Model/effort override denied | Omit inline overrides and use the profile's pins. |
| Fresh-context requirement denied | Use a compatible client and `fork_turns="none"`; legacy `fork_context` is not accepted. |
| Worktree mismatch | The session and guard script must resolve to the same Git worktree root. |
| Invalid input or unavailable policy | Check flag/policy JSON, TOMLs, Python version and worktree. The guard omits raw input from diagnostics. |
| `on` but no enforcement | Check project/hook trust, actual hook loading, tool-name match, interpreter availability and timeout behavior. |
| Model unavailable at provider | Check client, account/workspace and model/provider compatibility; setup and synthetic tests grant no access. |
| Native smoke refuses | Read the [prerequisites](validation.md#native-engine-matrix); extra hook or managed configuration needs review. |

Toggle errors can be generic; inspect malformed JSON/TOML locally. Remove sensitive content before sharing diagnostics. The package has no telemetry uploader or credential loader; normal Codex/provider activity has its own handling.

## Turn off and remove

Run `--off` while the project's guard script still exists and confirm the status. For full removal, review the [installed-file table](configuration.md#installed-project-files), then:

- Remove the exact Aperture hook entry, preserving other hooks.
- Remove the six package role bindings/files and defaults/features added solely for this package. Preserve settings still needed by other tools.
- Remove the marked Aperture section from `AGENTS.md`, preserving surrounding text.
- Remove the project flag, policy and guard script once no remaining hook references them.

Review the diff and restart. There is no destructive uninstall or stored snapshot that can decide which shared settings the project still needs. Removing the plugin through Codex affects its installation/cache, not the project cleanup above. Other worktrees and global configuration are not changed by this procedure.
