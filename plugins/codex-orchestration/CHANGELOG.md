# Changelog

## 0.2.0 — 2026-09-12

Renamed the plugin/package to `codex-orchestration` and its skills to `orchestration-setup`, `orchestration-delivery` and `orchestration-review`. Updated neutral author/display metadata, project guidance, installer markers, documentation, CI paths and catalog contracts. Global configuration and other repositories are outside this change.

Setup now refuses recognized `0.1.0` guidance or an existing legacy setup lock pending [manual migration](docs/operations.md#migrate-from-010). It holds both lock names during apply for cross-version exclusion. Existing policy/toggle values are preserved after migration. Generic agent names, model pins, guard logic and new-install default-off behavior are unchanged. No license has been selected.

## Standalone repository — 2026-09-12

Moved the selected package into the private Codex-Orchestration repository with its own single-plugin catalog. Updated repository metadata, installation instructions, configuration/customization, operations, validation and contributor/security guidance. Runtime assets, model pins, skills and the default-off guard remain unchanged at version 0.1.0. No distribution license has been selected.

## 0.1.0

Initial core under the prior plugin identity: portable team skills, six pinned Codex roles, preview-first project setup, and an optional default-off delegation guard allowing Luna, Terra and Sol. Project setup and hook trust remain explicit; advanced legacy workflows are not bundled.
