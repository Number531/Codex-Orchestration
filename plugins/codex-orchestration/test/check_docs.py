"""Check the repository's tracked Markdown documentation without network access.

Supported Markdown is deliberately small: ATX headings, inline ``[label](target)``
links, and fenced JSON or TOML examples. Reference links, HTML anchors, and link
targets with nested parentheses are outside this checker's scope.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.parse import unquote


FENCE_OPEN = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]+(?P<text>.*?)[ \t]*#*[ \t]*$")
INLINE_LINK = re.compile(r"\[[^\]\n]*\]\((?P<target>[^()\n]+)\)")
EXTERNAL_TARGET = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)


class DocumentationError(ValueError):
    """A local documentation reference or data example is invalid."""


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def tracked_markdown(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.md"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    files = [root / Path(name.decode("utf-8", "surrogateescape"))
             for name in result.stdout.split(b"\0") if name]
    for file in files:
        if not file.is_file():
            raise DocumentationError(f"{file.relative_to(root)}: tracked Markdown file is unreadable")
    return files


def closes_fence(line: str, marker: str) -> bool:
    character = re.escape(marker[0])
    return bool(re.match(rf"^ {{0,3}}{character}{{{len(marker)},}}[ \t]*$", line))


def heading_slugs(file: Path) -> set[str]:
    slugs: set[str] = set()
    marker: str | None = None
    for line in file.read_text(encoding="utf-8").splitlines():
        if marker:
            if closes_fence(line, marker):
                marker = None
            continue
        fence = FENCE_OPEN.match(line)
        if fence:
            marker = fence["marker"]
            continue
        heading = HEADING.match(line)
        if heading:
            slugs.add(slug(heading["text"]))
    return slugs


def slug(text: str) -> str:
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def local_target(source: Path, target: str, root: Path, line: int) -> tuple[Path, str | None] | None:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if EXTERNAL_TARGET.match(target):
        return None

    path, separator, fragment = target.partition("#")
    destination = source if not path else (source.parent / unquote(path)).resolve()
    try:
        destination.relative_to(root)
    except ValueError as error:
        raise DocumentationError(
            f"{source.relative_to(root)}:{line}: local link leaves the repository: {target}"
        ) from error
    if not destination.exists():
        raise DocumentationError(f"{source.relative_to(root)}:{line}: missing local link target: {target}")
    return destination, unquote(fragment).lower() if separator else None


def validate_example(file: Path, language: str, content: str, start_line: int, root: Path) -> None:
    try:
        if language == "json":
            json.loads(content)
        else:
            tomllib.loads(content)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        line = start_line + getattr(error, "lineno", 1) - 1
        raise DocumentationError(
            f"{file.relative_to(root)}:{line}: invalid {language} fenced example: {error}"
        ) from error


def check(root: Path | None = None) -> tuple[int, int]:
    """Validate tracked Markdown and return checked local-link and data-block counts."""
    root = (root or repository_root()).resolve()
    files = tracked_markdown(root)
    anchors = {file.resolve(): heading_slugs(file) for file in files}
    links = blocks = 0

    for file in files:
        marker: str | None = None
        language = ""
        example: list[str] = []
        example_start = 0
        for line_number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            if marker:
                if closes_fence(line, marker):
                    if language:
                        validate_example(file, language, "\n".join(example), example_start, root)
                        blocks += 1
                    marker = None
                    language = ""
                    example = []
                elif language:
                    example.append(line)
                continue

            fence = FENCE_OPEN.match(line)
            if fence:
                marker = fence["marker"]
                info = fence["info"].strip().split(maxsplit=1)
                language = info[0].lower() if info and info[0].lower() in {"json", "toml"} else ""
                example_start = line_number + 1
                continue

            for match in INLINE_LINK.finditer(line):
                resolved = local_target(file, match["target"], root, line_number)
                if resolved is None:
                    continue
                destination, fragment = resolved
                if fragment:
                    destination_anchors = anchors.get(destination, heading_slugs(destination))
                    if fragment not in destination_anchors:
                        raise DocumentationError(
                            f"{file.relative_to(root)}:{line_number}: missing local anchor in {match['target']}"
                        )
                links += 1

        if marker and language:
            raise DocumentationError(
                f"{file.relative_to(root)}:{example_start}: unclosed {language} fenced example"
            )

    return links, blocks


def main() -> int:
    try:
        links, blocks = check()
    except (DocumentationError, OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {links} local Markdown links/anchors and {blocks} JSON/TOML examples verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
