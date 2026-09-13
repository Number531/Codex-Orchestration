---
name: aperture-review
description: Independently audit a bounded change or verify its acceptance criteria using the configured Aperture specialist roles and executable evidence.
---

# Aperture independent review

Read the approved outcome, allowed scope, final diff and existing validation. Respect the project's owning workflow and finding vocabulary. Use `auditor` (Sol High) for adversarial defect discovery, or `verifier` (Terra Medium) for acceptance proof. Do not conflate an audit with verification or require both for every small edit.

Give the selected role a fresh self-contained packet with exact paths, relevant evidence, read-only authority, stopping condition and desired output; use `fork_turns="none"` without inline model/effort overrides. The role must not delegate again. Ask for bounded executable probes when inspection cannot establish behavior.

Require findings to cite evidence and distinguish observed failures from hypotheses. Use stable IDs and critical/major/minor/info severity. An audit returns a concrete acceptance condition per material defect; verification returns pass/fail/needs-evidence with criteria proven and missing evidence. No critical or major finding is silently waived. The parent reconciles results, performs authorized corrections and reruns affected checks within the existing scope and remediation budget.

Report unrun checks and compatibility limitations. Do not create an implementation contract, grant authority or perform remote actions as a side effect of review.
