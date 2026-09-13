# Changelog

## 0.2.1 — Unreleased

Separated installed-plugin and checkout setup instructions, documented project and hook trust separately, and stated the Unix prerequisite and default-off activation guidance. Added offline documentation checks and maintainer release/rollback instructions. The installer, hook, role profiles, model pins and project guidance are unchanged.

Disposable local-catalog and pinned GitHub-commit installation passed on CLI `0.154.0` and Desktop engine `0.154.0-alpha.6.2` on macOS: three cached skills, matching package files, repeatable setup and guard off. Desktop UI trust and live model access remain unqualified.

The repository became public on 2026-09-13 with Issues available, private vulnerability reporting enabled, and secret scanning/push protection verified. Updated public access, owner-controlled contribution and security-reporting guidance. Distribution license and tagged release remain pending; public visibility does not grant a project license.

## 0.2.0 — 2026-09-12

Renamed the plugin/package to `codex-orchestration` and its skills to `orchestration-setup`, `orchestration-delivery` and `orchestration-review`. Updated neutral author/display metadata, project guidance, installer markers, documentation, CI paths and catalog contracts. Global configuration and other repositories are outside this change.

Setup now refuses recognized `0.1.0` guidance or an existing legacy setup lock pending [manual migration](docs/operations.md#migrate-from-010). It holds both lock names during apply for cross-version exclusion. Existing policy/toggle values are preserved after migration. Generic agent names, model pins, guard logic and new-install default-off behavior are unchanged. No license has been selected.

## Standalone repository — 2026-09-12

Moved the selected package into the private Codex-Orchestration repository with its own single-plugin catalog. Updated repository metadata, installation instructions, configuration/customization, operations, validation and contributor/security guidance. Runtime assets, model pins, skills and the default-off guard remain unchanged at version 0.1.0. No distribution license has been selected.

## 0.1.0

Initial core under the prior plugin identity: portable team skills, six pinned Codex roles, preview-first project setup, and an optional default-off delegation guard allowing Luna, Terra and Sol. Project setup and hook trust remain explicit; advanced legacy workflows are not bundled.
