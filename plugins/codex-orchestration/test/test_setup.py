"""Synthetic filesystem contracts for the bounded Codex Orchestration project setup."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
SETUP_PATH = PACKAGE / "scripts" / "setup.py"
SPEC = importlib.util.spec_from_file_location("orchestration_setup", SETUP_PATH)
assert SPEC and SPEC.loader
setup = importlib.util.module_from_spec(SPEC)
import sys
sys.modules[SPEC.name] = setup
SPEC.loader.exec_module(setup)


class SetupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = setup.main(["--project", str(self.root), *args])
        return status, stdout.getvalue(), stderr.getvalue()

    def apply(self) -> None:
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 0, error)

    def controlled_bytes(self) -> dict[Path, bytes | None]:
        paths = list(setup.CONTROL_FILES) + [Path("AGENTS.md")]
        return {path: (self.root / path).read_bytes() if (self.root / path).exists() else None
                for path in paths}

    def test_preview_writes_nothing_and_apply_installs_fixed_inventory(self) -> None:
        before = self.controlled_bytes()
        status, output, error = self.invoke()
        self.assertEqual(status, 0, error)
        self.assertIn("Preview:", output)
        self.assertEqual(before, self.controlled_bytes())
        self.apply()
        for relative in setup.CONTROL_FILES:
            self.assertTrue((self.root / relative).is_file(), relative)
        self.assertIn(setup.BEGIN, (self.root / "AGENTS.md").read_text())
        self.assertEqual(False, json.loads((self.root / ".codex/delegation-guard.json").read_text())["enabled"])

    def test_rerun_is_byte_noop(self) -> None:
        self.apply()
        before = self.controlled_bytes()
        self.apply()
        self.assertEqual(before, self.controlled_bytes())

    def test_legacy_guidance_refuses_preview_and_apply_without_writes(self) -> None:
        for marker in ["<!-- aperture-agent-system:begin -->",
                       "<!-- aperture-agent-system:end -->",
                       f"{setup.BEGIN}\ncurrent\n{setup.END}\n<!-- aperture-agent-system:begin -->"]:
            with self.subTest(marker=marker):
                (self.root / "AGENTS.md").write_text("Keep project guidance.\n" + marker + "\n")
                before = self.controlled_bytes()
                for args in [(), ("--apply",)]:
                    status, _out, error = self.invoke(*args)
                    self.assertEqual(status, 1)
                    self.assertIn("legacy managed guidance", error)
                    self.assertEqual(before, self.controlled_bytes())
                    self.assertFalse((self.root / ".codex").exists())

    def test_legacy_lock_refuses_preview_and_apply_without_writes(self) -> None:
        lock = self.root / ".aperture-agent-system.setup.lock"
        for symlink in [False, True]:
            with self.subTest(symlink=symlink):
                if symlink:
                    lock.symlink_to(self.root / "missing-lock-target")
                else:
                    lock.write_text("old installer owns this lock")
                before = self.controlled_bytes()
                for args in [(), ("--apply",)]:
                    status, _out, error = self.invoke(*args)
                    self.assertEqual(status, 1)
                    self.assertIn("legacy setup lock", error)
                    self.assertEqual(before, self.controlled_bytes())
                self.assertTrue(lock.is_symlink() if symlink else lock.exists())
                lock.unlink()

    def test_legacy_state_appearing_after_preview_refuses_apply(self) -> None:
        for relative, content in [
            ("AGENTS.md", "<!-- aperture-agent-system:begin -->\nold guidance\n"),
            (".aperture-agent-system.setup.lock", "old installer running"),
        ]:
            with self.subTest(relative=relative):
                changes = setup.plan_setup(self.root)
                legacy = self.root / relative
                legacy.write_text(content)
                before = self.controlled_bytes()
                with self.assertRaisesRegex(setup.SetupError, "legacy"):
                    setup.apply_changes(self.root, changes)
                self.assertEqual(before, self.controlled_bytes())
                self.assertEqual(legacy.read_text(), content)
                self.assertFalse((self.root / ".codex-orchestration.setup.lock").exists())
                legacy.unlink()

    def test_manual_legacy_guidance_migration_preserves_flag_and_policy(self) -> None:
        self.apply()
        agents = self.root / "AGENTS.md"
        old = "<!-- aperture-agent-system:begin -->\nlegacy guidance\n<!-- aperture-agent-system:end -->\n"
        agents.write_text("Keep project guidance.\n\n" + old)
        flag = self.root / ".codex/delegation-guard.json"
        policy = self.root / ".codex/delegation-policy.json"
        flag.write_bytes(b'{"enabled": true}\n')
        policy.write_bytes(b'{"allowed_models": ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "custom-model"]}\n')
        before_flag, before_policy = flag.read_bytes(), policy.read_bytes()
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("legacy managed guidance", error)
        # The operator reviews/removes the old block; setup does not migrate it.
        agents.write_text("Keep project guidance.\n\n")
        self.apply()
        self.assertTrue(agents.read_text().startswith("Keep project guidance.\n\n"))
        self.assertEqual(agents.read_text().count(setup.BEGIN), 1)
        self.assertNotIn("aperture-agent-system", agents.read_text())
        self.assertEqual(flag.read_bytes(), before_flag)
        self.assertEqual(policy.read_bytes(), before_policy)

    def test_both_lock_names_exclude_installers_during_writes(self) -> None:
        legacy = self.root / ".aperture-agent-system.setup.lock"
        current = self.root / ".codex-orchestration.setup.lock"
        original = setup._write_atomic
        def observe_locks(path: Path, content: bytes) -> None:
            for lock in [legacy, current]:
                self.assertTrue(lock.is_file())
                # This is the exclusive-create primitive used by both versions.
                with self.assertRaises(FileExistsError):
                    os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            original(path, content)
        setup._write_atomic = observe_locks
        try:
            self.apply()
        finally:
            setup._write_atomic = original
        self.assertFalse(legacy.exists())
        self.assertFalse(current.exists())

    def test_merges_existing_config_hooks_and_agents_without_losing_text(self) -> None:
        codex = self.root / ".codex"
        codex.mkdir()
        config = codex / "config.toml"
        source_config = tomllib.loads((PACKAGE / "assets/project/.codex/config.toml").read_text())
        initial = ("# retain this comment\n[features]\n# current setting follows\n\n"
                   "[agents]\nmax_threads = 6\n\n[agents.default]\n"
                   f"description = {source_config['agents']['default']['description']!r}\n\n"
                   "[custom]\nkeep = \"yes\"")
        config.write_text(initial)
        config.chmod(0o640)
        (codex / "hooks.json").write_text(json.dumps({"hooks": {"PostToolUse": [{"command": "keep"}]}, "custom": True}))
        (self.root / "AGENTS.md").write_text("Existing project guidance.\n")
        self.apply()
        result = config.read_text()
        self.assertTrue(result.startswith("# retain this comment\n[features]\n# current setting follows\n\n"))
        self.assertIn("retain this comment", result)
        self.assertIn("keep = \"yes\"", result)
        self.assertIn("multi_agent = true", result)
        parsed = tomllib.loads(result)
        self.assertTrue(parsed["features"]["multi_agent_v2"])
        self.assertEqual(parsed["agents"]["default"]["config_file"], "agents/default.toml")
        self.assertEqual(parsed["custom"]["keep"], "yes")
        self.assertEqual(config.stat().st_mode & 0o777, 0o640)
        hooks = json.loads((codex / "hooks.json").read_text())
        self.assertTrue(hooks["custom"])
        self.assertEqual("keep", hooks["hooks"]["PostToolUse"][0]["command"])
        agents = (self.root / "AGENTS.md").read_text()
        self.assertTrue(agents.startswith("Existing project guidance."))
        self.assertEqual(agents.count(setup.BEGIN), 1)

    def test_any_conflict_aborts_entire_preflight(self) -> None:
        target = self.root / ".codex/agents/default.toml"
        target.parent.mkdir(parents=True)
        target.write_text("different = true\n")
        before = self.controlled_bytes()
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("conflicting owned file", error)
        self.assertEqual(before, self.controlled_bytes())

    def test_existing_flag_and_custom_policy_survive(self) -> None:
        codex = self.root / ".codex"
        codex.mkdir()
        flag = b'{"enabled": true}\n'
        policy = b'{"allowed_models": ["gpt-5.6-luna", "custom.review"]}\n'
        (codex / "delegation-guard.json").write_bytes(flag)
        (codex / "delegation-policy.json").write_bytes(policy)
        self.apply()
        self.assertEqual((codex / "delegation-guard.json").read_bytes(), flag)
        self.assertEqual((codex / "delegation-policy.json").read_bytes(), policy)

    def test_malformed_schema_unsafe_paths_size_and_inline_toml_are_rejected(self) -> None:
        cases: list[tuple[Path, bytes, str]] = [
            (Path(".codex/delegation-guard.json"), b'{"enabled": "yes"}', "enabled boolean"),
            (Path(".codex/delegation-policy.json"), b'{"allowed_models": []}', "allowed_models"),
            (Path(".codex/config.toml"), b'features = { multi_agent = true }\n', "unsupported inline"),
            (Path(".codex/config.toml"), b"x" * (setup.LIMIT + 1), "exceeds 1 MiB"),
        ]
        for relative, content, expected in cases:
            with self.subTest(relative=relative, expected=expected):
                self.tearDown()
                self.setUp()
                target = self.root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                status, _out, error = self.invoke("--apply")
                self.assertEqual(status, 1)
                self.assertIn(expected, error)

        self.tearDown()
        self.setUp()
        target = self.root / ".codex"
        target.symlink_to(self.root / "elsewhere", target_is_directory=True)
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("symlink", error)

    def test_dotted_or_quoted_toml_layout_and_required_value_conflict_are_rejected(self) -> None:
        cases = [
            b"features.multi_agent = true\n",
            b'"features" = { multi_agent = true }\n',
            b"[features]\nmulti_agent = false\n",
        ]
        for content in cases:
            with self.subTest(content=content):
                self.tearDown()
                self.setUp()
                target = self.root / ".codex/config.toml"
                target.parent.mkdir(parents=True)
                target.write_bytes(content)
                status, _out, error = self.invoke("--apply")
                self.assertEqual(status, 1)
                self.assertTrue("unsupported" in error or "conflicting required" in error)

    def test_symlinked_project_root_and_control_file_are_rejected(self) -> None:
        alias = self.root.parent / "project-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = setup.main(["--project", str(alias), "--apply"])
        self.assertEqual(status, 1)
        self.assertIn("real Git-root", stderr.getvalue())

        codex = self.root / ".codex"
        codex.mkdir()
        policy = codex / "delegation-policy.json"
        policy.symlink_to(self.root / "outside-policy.json")
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("symlink", error)

    def test_root_lock_is_transient_and_supports_git_file_worktrees(self) -> None:
        linked = self.root.parent / "linked-project"
        metadata = self.root.parent / "linked-git-dir"
        linked.mkdir()
        subprocess.run(["git", "init", "-q", f"--separate-git-dir={metadata}", str(linked)], check=True)
        git_file = linked / ".git"
        before = git_file.read_bytes()
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = setup.main(["--project", str(linked), "--apply"])
        self.assertEqual(status, 0, stderr.getvalue())
        self.assertEqual(git_file.read_bytes(), before)
        self.assertFalse((linked / ".codex-orchestration.setup.lock").exists())
        self.assertTrue((linked / ".codex/config.toml").exists())

    def test_symlink_or_existing_root_lock_refuses_without_writes(self) -> None:
        lock = self.root / ".codex-orchestration.setup.lock"
        lock.symlink_to(self.root / "elsewhere")
        before = self.controlled_bytes()
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("symlink setup lock", error)
        self.assertEqual(before, self.controlled_bytes())
        self.assertFalse((self.root / ".aperture-agent-system.setup.lock").exists())
        lock.unlink()
        lock.write_text("stale")
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("stale lock", error)
        self.assertFalse((self.root / ".aperture-agent-system.setup.lock").exists())

    def test_changed_original_after_preflight_is_refused_before_any_write(self) -> None:
        changes = setup.plan_setup(self.root)
        changes[0].target.parent.mkdir(parents=True)
        changes[0].target.write_bytes(b"editor change")
        with self.assertRaisesRegex(setup.SetupError, "changed after preview"):
            setup.apply_changes(self.root, changes)
        self.assertEqual(changes[0].target.read_bytes(), b"editor change")
        self.assertFalse((self.root / ".codex-orchestration.setup.lock").exists())

    def test_hooks_guard_mentions_across_other_events_conflict(self) -> None:
        asset = json.loads((PACKAGE / "assets/project/.codex/hooks.json").read_text())
        guard = asset["hooks"]["PreToolUse"][0]
        target = self.root / ".codex/hooks.json"
        target.parent.mkdir()
        target.write_text(json.dumps({"hooks": {"PreToolUse": [guard], "PostToolUse": [guard]}}))
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("ambiguous", error)

    def test_oversized_merged_agents_output_is_refused(self) -> None:
        (self.root / "AGENTS.md").write_text("x" * (setup.LIMIT - 8))
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("planned output exceeds", error)

    def test_changed_or_malformed_managed_agents_block_is_rejected(self) -> None:
        (self.root / "AGENTS.md").write_text(f"{setup.BEGIN}\nchanged\n{setup.END}\n")
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("changed managed", error)
        (self.root / "AGENTS.md").write_text(f"{setup.BEGIN}\nonly one marker\n")
        status, _out, error = self.invoke("--apply")
        self.assertEqual(status, 1)
        self.assertIn("malformed", error)

    def test_apply_failure_rolls_back_only_its_own_writes(self) -> None:
        changes = setup.plan_setup(self.root)
        original = setup._write_atomic
        calls = 0
        def fail_second(path: Path, content: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic write failure")
            original(path, content)
        setup._write_atomic = fail_second
        try:
            with self.assertRaises(setup.SetupError):
                setup.apply_changes(self.root, changes)
        finally:
            setup._write_atomic = original
        self.assertEqual(self.controlled_bytes(), {path: None for path in self.controlled_bytes()})
        self.assertFalse((self.root / ".aperture-agent-system.setup.lock").exists())
        self.assertFalse((self.root / ".codex-orchestration.setup.lock").exists())

    def test_rollback_refuses_to_replace_an_intervening_edit(self) -> None:
        changes = setup.plan_setup(self.root)
        original = setup._write_atomic
        calls = 0
        def edit_then_fail(path: Path, content: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                changes[0].target.write_bytes(b"editor change")
                raise OSError("synthetic write failure")
            original(path, content)
        setup._write_atomic = edit_then_fail
        try:
            with self.assertRaisesRegex(setup.SetupError, "rollback refused"):
                setup.apply_changes(self.root, changes)
        finally:
            setup._write_atomic = original
        self.assertEqual(changes[0].target.read_bytes(), b"editor change")


if __name__ == "__main__":
    unittest.main()
