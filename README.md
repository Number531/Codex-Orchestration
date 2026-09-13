# Codex-Orchestration

Cost-aware delegation for Codex, with named specialist agents and an optional model guard. This standalone repository contains only the **Codex-Orchestration** plugin and its documentation.

An orchestrating agent can choose tasks dynamically while delegating through registered roles with fixed model and reasoning settings. The optional guard rejects covered spawn requests that violate the project policy. **Enforcement starts off.**

This repository is initially private. GitHub read access is required until the owner changes its visibility. It is a repository-hosted Codex catalog, not a public directory listing or an OpenAI endorsement. No license has been selected for public distribution yet.

## Start here

| Goal | Guide |
|---|---|
| Understand the package and install it | [Codex Orchestration quick start](plugins/codex-orchestration/README.md) |
| Choose roles, toggle the guard, or add a custom agent | [Configuration](plugins/codex-orchestration/docs/configuration.md) |
| Update, troubleshoot, or remove project assets | [Operations and recovery](plugins/codex-orchestration/docs/operations.md) |
| Understand what has actually been tested | [Validation and compatibility](plugins/codex-orchestration/docs/validation.md) |
| Contribute a change | [Contributing](CONTRIBUTING.md) |
| Report a security concern | [Security](SECURITY.md) |

## Install the plugin

First review the [client and model prerequisites](plugins/codex-orchestration/README.md#requirements). These commands register the repository catalog and install its skill package:

```sh
codex plugin marketplace add https://github.com/Number531/Codex-Orchestration.git
codex plugin list --available --json --marketplace codex-orchestration
codex plugin add codex-orchestration@codex-orchestration
```

For a private repository, use Git credentials with read access. SSH is also supported:

```sh
codex plugin marketplace add git@github.com:Number531/Codex-Orchestration.git
```

Choose one catalog source. If that catalog is already registered, inspect `codex plugin marketplace list` before adding it again. Plugin installation makes three skills available; it does not apply project configuration, grant hook trust, or enable enforcement. Continue with the [project setup steps](plugins/codex-orchestration/README.md#set-up-one-project).

## Repository and package identities

| Item | Value |
|---|---|
| GitHub repository | `Number531/Codex-Orchestration` |
| Codex marketplace name | `codex-orchestration` |
| Plugin ID | `codex-orchestration` |
| Package directory | `plugins/codex-orchestration/` |
| Native catalog | `.agents/plugins/marketplace.json` |

Version `0.2.0` aligns the plugin, skills and project markers with this repository's community branding. Existing `0.1.0` installations need the [manual migration steps](plugins/codex-orchestration/docs/operations.md#migrate-from-010). The generic role names, model pins and default-off behavior are unchanged. This repository contains no sibling plugins from the original multi-plugin repository.

## Development checks

From the repository root, with Python 3.11+ and Git:

```sh
python3 -B -m unittest discover -s plugins/codex-orchestration/test -p 'test_*.py'
python3 -B plugins/codex-orchestration/test/check_catalog.py
```

These checks use synthetic local fixtures and run in [GitHub Actions](.github/workflows/validate.yml). CI does not run paid models or native Codex sessions. Native engine checks, Desktop installation/trust, and live model access are separate validation surfaces; see the [compatibility guide](plugins/codex-orchestration/docs/validation.md).

## Before a public release

Choose a license and update the package metadata, confirm branding and source ownership, test onboarding with a separate account, and review the repository contents and history before changing visibility. Publishing to GitHub and submitting to OpenAI's public plugin directory are separate decisions. See [maintainer release guidance](CONTRIBUTING.md#release-preparation).
