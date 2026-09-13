# Security

## Scope and trust

The plugin installs reviewed project-local agent settings and an optional hook. The guard is off initially. Setup does not grant Codex trust or configure global enforcement. Effective protection depends on the client loading the intended hook, trusting it, matching the covered spawn path and respecting its synchronous result.

The guard is not a billing ceiling, hostile-process sandbox or account-wide policy. It does not cover arbitrary API calls or every way to start another session. The original tests establish bounded behavior on specific engines; see [validation](plugins/codex-orchestration/docs/validation.md).

The shipped installer and guard make no network calls and load no credentials. Codex, Git authentication and the chosen model provider have their own data handling. The native test harness uses loopback fixtures and may leave synthetic local session records; do not upload those records without review.

## Report a vulnerability

Use GitHub's private vulnerability reporting for this repository if that option is enabled. While the repository is private, an authorized collaborator can contact the owner through their established private channel. If no private reporting channel is available, open only a minimal, non-sensitive issue requesting one; do not include exploit details, credentials or customer data.

Provide the affected package/client versions, a sanitized reproduction, the violated boundary and observed impact through the private channel. Do not publish a working exploit or sensitive logs in a public issue. This initial project makes no response-time or long-term support commitment.
