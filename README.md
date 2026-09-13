# Codex-Orchestration

Cost-aware delegation for Codex, with named specialist agents and an optional model guard. This standalone repository contains only the **Codex-Orchestration** plugin and its documentation.

An orchestrating agent can choose tasks dynamically while delegating through registered roles with fixed model and reasoning settings. The optional guard rejects covered spawn requests that violate the project policy. **Enforcement starts off.**

This repository is public and accepts community issue reports. It is a repository-hosted Codex catalog; an OpenAI public-directory listing and endorsement have not been granted. Distribution terms remain under review; see [licensing status](#licensing-status).

## Start here

| Goal | Guide |
|---|---|
| Understand the package and install it | [Codex Orchestration quick start](plugins/codex-orchestration/README.md) |
| Choose roles, toggle the guard, or add a custom agent | [Configuration](plugins/codex-orchestration/docs/configuration.md) |
| Update, troubleshoot, or remove project assets | [Operations and recovery](plugins/codex-orchestration/docs/operations.md) |
| Understand what has actually been tested | [Validation and compatibility](plugins/codex-orchestration/docs/validation.md) |
| Contribute a change | [Contributing](CONTRIBUTING.md) |
| Report a security concern | [Security](SECURITY.md) |
| Report a bug or request an improvement | [GitHub Issues](https://github.com/Number531/Codex-Orchestration/issues) |

## Install the plugin

First review the [client and model prerequisites](plugins/codex-orchestration/README.md#requirements). These commands register the repository catalog and install its skill package:

```sh
codex plugin marketplace add https://github.com/Number531/Codex-Orchestration.git
codex plugin list --available --json --marketplace codex-orchestration
codex plugin add codex-orchestration@codex-orchestration
```

The HTTPS catalog is publicly readable and requires no repository invitation. SSH is also supported for users with GitHub SSH authentication:

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

Version `0.2.0` aligned the plugin, skills and project markers with this repository's community branding. Existing `0.1.0` installations need the [manual migration steps](plugins/codex-orchestration/docs/operations.md#migrate-from-010). The generic role names, model pins and default-off behavior are unchanged. This repository contains no sibling plugins from the original multi-plugin repository.

## Reviewed versions

For a reproducible install, add `--ref <reviewed-ref>` to the marketplace-add command above. Replace the placeholder with a reviewed commit SHA or a published tag from [Releases](https://github.com/Number531/Codex-Orchestration/releases); use one catalog source. No tagged release has been published yet. Review the [upgrade and rollback procedure](plugins/codex-orchestration/docs/operations.md#upgrade-a-project) before changing an existing installation. Maintainers use the [release procedure](docs/releasing.md).

## Development checks

From the repository root, with Python 3.11+ and Git:

```sh
python3 -B -m unittest discover -s plugins/codex-orchestration/test -p 'test_*.py'
python3 -B plugins/codex-orchestration/test/check_catalog.py
python3 -B plugins/codex-orchestration/test/check_docs.py
```

These checks use synthetic local fixtures and run in [GitHub Actions](.github/workflows/validate.yml). CI does not run paid models or native Codex sessions. Native engine checks, Desktop installation/trust, and live model access are separate validation surfaces; see the [compatibility guide](plugins/codex-orchestration/docs/validation.md).

## Licensing status

A distribution license reflecting the owner's intended free-use and enterprise restrictions is still being selected. No project license has been adopted. Public visibility does not itself grant general reuse or redistribution rights; GitHub explains the [default licensing position and platform fork rights](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

Before a versioned release, finalize the license and package metadata, confirm source ownership, and record supported-client validation. Desktop UI and live-account qualification remain open. See [maintainer release guidance](CONTRIBUTING.md#release-preparation). Publishing a GitHub release and submitting to OpenAI's public plugin directory are separate decisions.
