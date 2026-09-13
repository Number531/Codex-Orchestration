# Releasing Codex-Orchestration

Release only a reviewed commit of this single plugin. A tag selects a repository snapshot; the plugin version, both manifests, catalog entry and changelog must agree on the release version.

## Prepare and validate

1. Confirm the license, attribution and intended distribution audience. Review the candidate tree and reachable history for sensitive material; a pattern scan does not establish ownership or prove that every secret is absent.
2. Update both package manifests, the catalog version, changelog and affected onboarding/compatibility documentation. Keep delegation enforcement off by default.
3. Run the deterministic checks from the repository root:

```sh
python3 -B -m unittest discover -s plugins/codex-orchestration/test -p 'test_*.py'
python3 -B plugins/codex-orchestration/test/check_catalog.py
python3 -B plugins/codex-orchestration/test/check_docs.py
git diff --check
```

4. Trial discovery, installation, project setup and default-off status in an isolated configuration/cache and disposable Git project. Confirm that the installed cache matches the reviewed package. Record exact client/OS versions and distinguish CLI, Desktop engine and Desktop UI results. Native and live checks remain opt-in; keep credentials and session records out of release artifacts.
5. Obtain independent review, open a pull request and require passing CI before merging. Confirm the merged tree is the reviewed tree. Keep main protected and do not bypass failing required checks.

## Publish a reviewed version

After the owner authorizes publication, create a version tag such as `vX.Y.Z` at the exact validated merge commit and publish a GitHub release using that tag. Replace placeholders with the reviewed version and commit. Do not move or force-update a published tag; ship a new version for corrections.

The release notes should state the change, migration requirements, tested client/OS versions, known limitations, license and default-off behavior. Verify the release and tag resolve to the intended commit, then trial catalog discovery from that tag. GitHub's generated source archives are sufficient for this package; no custom binary build pipeline is required.

Users can add `--ref <release-tag>` to the documented marketplace-add command to select a reviewed version. A pinned catalog remains on that ref when refreshed; moving to another release requires reviewing and updating the catalog source/ref through the client's supported marketplace flow. Plugin-cache updates and project-asset updates are separate.

## Repository security settings

Maintain pull-request-only changes to main, the required `contracts` check from GitHub Actions, resolved review conversations, and blocked force-pushes/deletions. A solo maintainer may use zero required approvals while retaining independent review in the contribution process; require an additional reviewer when one is available.

When the repository is public, enable GitHub private vulnerability reporting and verify its reporting link before advertising it in SECURITY.md. Confirm secret scanning and repository push protection in Security settings. Public and private repository availability differs; do not claim a feature is active solely because a policy file mentions it, or enroll in a paid product unintentionally.

Changing repository visibility, publishing a release and submitting to OpenAI's public plugin directory are separate owner-authorized actions. A repository catalog is not an OpenAI directory listing.

## Roll back an adoption

Review the [project upgrade and recovery guide](../plugins/codex-orchestration/docs/operations.md#upgrade-a-project). Select the prior reviewed package version for the plugin cache and separately reconcile its project files, preserving custom roles, policy and toggle values. Disabling the plugin does not remove project assets. If reverting enforcement, explicitly set the project's guard off before removing its script/hook. Never use blanket cleanup or history rewriting to discard unrelated work.
