# Contributing

This repository maintains one plugin: `plugins/codex-orchestration/`. Keep changes focused on its existing project setup, delegation, documentation and validation responsibilities. The repository is initially private; collaboration requires access. A distribution license must be selected before the planned public release.

## Local development

Use Python 3.11+ and Git. No Python packages are needed for the deterministic tests. Work on a branch and use disposable Git projects for setup experiments.

```sh
python3 -B -m unittest discover -s plugins/codex-orchestration/test -p 'test_*.py'
python3 -B plugins/codex-orchestration/test/check_catalog.py
git diff --check
```

Read [validation and compatibility](plugins/codex-orchestration/docs/validation.md) before running native or live checks. Do not automatically invoke paid services, change global trust, install the plugin for someone else, or update their real project as part of a test.

GitHub Actions runs the deterministic unit and catalog checks on pushes and pull requests using Python 3.11. Its token has read-only repository access, checkout does not persist credentials, and action dependencies are pinned. Native/live checks remain opt-in; a green CI run does not qualify a desktop client.

## Changes and pull requests

Explain the user-visible problem, the resulting behavior, affected files and executable validation. Report unrun tests and compatibility limits. Include a regression test for a meaningful behavioral fix and update the relevant user guide. Documentation-only changes should check relative links, command examples and consistency with the implementation.

Preserve the default-off flag, existing project content, explicit trust boundary, scoped authorization and normal permission handling. Hook/profile/policy changes deserve independent review because they affect delegation behavior. Do not claim a deny rule covers clients or execution paths that were not tested.

Keep the portable `plugin.json` and `.codex-plugin/plugin.json` identity/version fields consistent. Maintain the single-entry `.agents/plugins/marketplace.json` catalog and its package-relative source path. The marketplace and plugin ID are both `codex-orchestration`. Keep portable project guidance independent of a maintainer's global instructions, standing billing permissions and unrelated specialist profiles.

Avoid adding a workflow framework, automatic updater, account-wide control claim or global installer without an explicit supported use case and appropriate tests. Never include credentials, `.env` files, local session records, model caches, customer source, or machine-specific paths in a contribution. See [Security](SECURITY.md).

## Report a problem

Use an issue in this repository for a non-sensitive bug or documentation problem. Include OS, package/client versions, the failing command, expected/observed behavior and a minimal sanitized reproduction. Do not attach full user configuration, prompts or logs containing secrets. Security-sensitive details belong in a private report.

## Release preparation

Before a public launch:

1. Confirm the intended license and ownership/branding permissions, add the selected license, and align manifest metadata and documentation. No license is selected by this initial extraction.
2. Review the complete candidate tree and reachable history for credentials, customer data, internal material and third-party content. This repository starts from selected package files rather than importing the original repository's history.
3. Pass deterministic checks, review the final diff independently, and record native/client validation honestly. Resolve or explicitly disclose compatibility assumptions.
4. Trial the documented install, setup, trust, toggle, update and removal procedures in a disposable project with a separate authorized account. Confirm that the configured models are available there.
5. Review the release notes and versioned artifacts. Changing repository visibility, publishing a release, and applying to OpenAI's public plugin directory require separate owner decisions.

OpenAI's [submission documentation](https://developers.openai.com/plugins/deploy/submission) describes directory review and publication. A repository catalog or public GitHub repository is not itself a directory approval. Record the actual distribution state rather than advertising an unapproved listing.
