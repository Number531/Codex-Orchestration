"""Regression coverage for the offline Markdown documentation checker."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("docs_check", PACKAGE / "test/check_docs.py")
assert SPEC and SPEC.loader
docs_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs_check)


class DocumentationCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="orchestration-docs-")
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_tracked(self, relative: str, content: str) -> None:
        file = self.root / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", relative], check=True)

    def test_rejects_missing_local_link(self) -> None:
        self.write_tracked("README.md", "# Start\n[Missing](missing.md)\n")
        with self.assertRaisesRegex(docs_check.DocumentationError, r"README.md:2: missing local link target"):
            docs_check.check(self.root)

    def test_rejects_missing_local_anchor(self) -> None:
        self.write_tracked("README.md", "# Start\n[Target](guide.md#not-here)\n")
        self.write_tracked("guide.md", "# Elsewhere\n")
        with self.assertRaisesRegex(docs_check.DocumentationError, r"README.md:2: missing local anchor"):
            docs_check.check(self.root)

    def test_rejects_invalid_json_and_toml_examples(self) -> None:
        for language, content in [("json", '{"enabled": }'), ("toml", "enabled =")]:
            with self.subTest(language=language):
                self.write_tracked("README.md", f"# Start\n```{language}\n{content}\n```\n")
                with self.assertRaisesRegex(docs_check.DocumentationError, rf"README.md:3: invalid {language}"):
                    docs_check.check(self.root)

    def test_ignores_link_shaped_shell_text_inside_a_fence(self) -> None:
        self.write_tracked("README.md", "# Start\n```sh\necho '[not-a-link](missing.md)'\n```\n")
        self.assertEqual((0, 0), docs_check.check(self.root))


if __name__ == "__main__":
    unittest.main()
