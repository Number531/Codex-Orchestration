---
name: aperture-setup
description: Preview and explicitly install Aperture team guidance, pinned Codex agents and the optional delegation guard into a Git project.
---

# Aperture setup

Use for requested Aperture installation, configuration review or setup diagnostics. Resolve the plugin root as two directories above this SKILL.md; do not assume the plugin cache is in the project. Read the plugin README and inspect the target project's instructions and existing `.codex` configuration.

1. Run `python3 <plugin-root>/scripts/setup.py --project <absolute-git-root>` to preview. This is read-only by default.
2. Explain the concrete additions and conflicts. If project setup is already authorized, apply the clean preview using the same command plus `--apply`. Otherwise obtain authorization for the displayed durable changes. Never force over a conflict; resolve it through a separately reviewed project edit and preview again.
3. Verify the resulting project diff. Setup installs profiles and a hook definition with the guard off; native project/hook trust is a separate Codex user decision.
4. Enable enforcement only when the user has authorized it: `python3 <project>/.agents/system/hooks/delegation_guard.py --on`. Use `--status` to inspect and `--off` to disable. Start a fresh Codex session after profile/config changes.

Do not install into global settings, export credentials, trust hooks automatically, or assume plugin enablement activates the guard. Preserve project policy and instructions. On rerun, changed assets are conflicts for review; the installer does not overwrite customizations or reset the toggle.
