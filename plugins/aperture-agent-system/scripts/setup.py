#!/usr/bin/env python3
"""Preview or safely install Aperture project-local configuration.

The installer deliberately supports only the small, portable asset inventory in
this package.  It is a cooperative installer: it detects conflicting edits
instead of attempting a general configuration migration.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
from typing import Any


LIMIT = 1024 * 1024
PACKAGE = Path(__file__).resolve().parents[1]
ASSETS = PACKAGE / "assets"
PROJECT_ASSETS = ASSETS / "project"
BEGIN = "<!-- aperture-agent-system:begin -->"
END = "<!-- aperture-agent-system:end -->"
ROLE_NAMES = ("default", "explorer", "worker", "implementer", "auditor", "verifier")
CONTROL_FILES = (
    Path(".codex/config.toml"),
    Path(".codex/delegation-guard.json"),
    Path(".codex/delegation-policy.json"),
    Path(".codex/hooks.json"),
    *(Path(".codex/agents") / (name + ".toml") for name in ROLE_NAMES),
    Path(".agents/system/hooks/delegation_guard.py"),
)
TABLE = re.compile(r"^\s*\[([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\]\s*(?:#.*)?$")
SIMPLE_ASSIGNMENT = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*=(?!\s*\{)\s*")
MODEL = re.compile(r"[a-z0-9][a-z0-9.-]*\Z")


class SetupError(RuntimeError):
    """A safe preflight failure that leaves the project untouched."""


@dataclass(frozen=True)
class Change:
    target: Path
    content: bytes
    before: bytes | None
    reason: str


def _not_link_regular(path: Path, *, missing_ok: bool = False) -> None:
    if not path.exists() and not path.is_symlink():
        if missing_ok:
            return
        raise SetupError(f"missing required file: {path}")
    info = path.lstat()
    if path.is_symlink() or not path.is_file():
        raise SetupError(f"refusing symlink or non-regular file: {path}")
    if info.st_size > LIMIT:
        raise SetupError(f"file exceeds 1 MiB bound: {path}")


def _safe_dir(path: Path, root: Path, *, create_ok: bool) -> None:
    """Check existing parents up to root; missing parents may be created later."""
    if not path.is_absolute() or not root.is_absolute() or not path.is_relative_to(root):
        raise SetupError(f"path escapes project root: {path}")
    current = path
    missing: list[Path] = []
    while current != root:
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise SetupError(f"refusing symlink or non-directory control path: {current}")
        else:
            missing.append(current)
        current = current.parent
    if current != root:
        raise SetupError(f"path escapes project root: {path}")
    if root.is_symlink() or not root.is_dir():
        raise SetupError("project root must be a real directory")
    if missing and not create_ok:
        return


def read_file(path: Path, *, missing_ok: bool = False) -> bytes | None:
    _not_link_regular(path, missing_ok=missing_ok)
    if not path.exists() and not path.is_symlink():
        return None
    with path.open("rb") as handle:
        data = handle.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise SetupError(f"file exceeds 1 MiB bound: {path}")
    return data


def _utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SetupError(f"{label} must be UTF-8") from error


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(_utf8(data, label))
    except json.JSONDecodeError as error:
        raise SetupError(f"invalid JSON in {label}") from error
    if not isinstance(value, dict):
        raise SetupError(f"{label} must be a JSON object")
    return value


def validate_flag(data: bytes, label: str) -> dict[str, Any]:
    value = _json_object(data, label)
    if set(value) != {"enabled"} or type(value["enabled"]) is not bool:
        raise SetupError(f"{label} must contain only an enabled boolean")
    return value


def validate_policy(data: bytes, label: str) -> dict[str, Any]:
    value = _json_object(data, label)
    models = value.get("allowed_models")
    if (set(value) != {"allowed_models"} or not isinstance(models, list)
            or not 1 <= len(models) <= 32
            or any(not isinstance(item, str) or not MODEL.fullmatch(item) for item in models)
            or len(set(models)) != len(models)):
        raise SetupError(f"{label} must contain a nonempty unique allowed_models list")
    return value


def _toml(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = tomllib.loads(_utf8(data, label))
    except tomllib.TOMLDecodeError as error:
        raise SetupError(f"invalid TOML in {label}") from error
    if not isinstance(value, dict):
        raise SetupError(f"{label} must be a TOML table")
    return value


def _semantic_merge(existing: dict[str, Any], required: dict[str, Any], where: str = "") -> dict[str, Any]:
    merged = copy.deepcopy(existing)
    for key, wanted in required.items():
        label = f"{where}.{key}" if where else key
        if key not in merged:
            merged[key] = copy.deepcopy(wanted)
        elif isinstance(wanted, dict):
            if not isinstance(merged[key], dict):
                raise SetupError(f"conflicting required TOML table: {label}")
            merged[key] = _semantic_merge(merged[key], wanted, label)
        elif merged[key] != wanted or type(merged[key]) is not type(wanted):
            raise SetupError(f"conflicting required TOML value: {label}")
    return merged


def _render_toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_render_toml_value(item) for item in value) + "]"
    raise SetupError("asset config contains unsupported TOML value")


def merge_toml(existing_bytes: bytes, required_bytes: bytes) -> bytes:
    """Insert only absent simple config keys/tables and prove its semantic result."""
    existing = _toml(existing_bytes, "existing config")
    required = _toml(required_bytes, "package config")
    expected = _semantic_merge(existing, required)
    text = _utf8(existing_bytes, "existing config")
    lines = text.splitlines(keepends=True)
    headers: list[tuple[tuple[str, ...], int]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = TABLE.match(line)
        if match:
            headers.append((tuple(match.group(1).split(".")), index))
            continue
        if (stripped.startswith("[") or "=" not in line
                or SIMPLE_ASSIGNMENT.match(line) is None):
            raise SetupError("unsupported inline, dotted-key, or array-table TOML layout; integrate manually")
    if existing == expected:
        return existing_bytes
    header_index = dict(headers)

    additions: list[tuple[tuple[str, ...], list[tuple[str, Any]]]] = []
    def walk(table: dict[str, Any], path: tuple[str, ...] = ()) -> None:
        source = existing
        for part in path:
            source = source.get(part, {}) if isinstance(source, dict) else {}
        absent = [(key, value) for key, value in table.items()
                  if not isinstance(value, dict) and key not in source]
        if absent:
            additions.append((path, absent))
        for key, value in table.items():
            if isinstance(value, dict):
                walk(value, path + (key,))
    walk(required)

    # All positions refer to the original lines. Applying them in reverse means
    # no insertion changes a position we have yet to use.
    insertions: list[tuple[int, str]] = []
    append: list[str] = []
    for path, entries in additions:
        rendered = [f"{key} = {_render_toml_value(value)}\n" for key, value in entries]
        if path in header_index:
            start = header_index[path] + 1
            end = next((position for _name, position in headers if position >= start), len(lines))
            prefix = "\n" if end and not lines[end - 1].endswith("\n") else ""
            insertions.append((end, prefix + "".join(rendered)))
        else:
            if append:
                append.append("\n")
            append.append("[" + ".".join(path) + "]\n")
            append.extend(rendered)
    for position, content in sorted(insertions, reverse=True):
        lines.insert(position, content)
    result_text = "".join(lines)
    if append:
        if result_text and not result_text.endswith("\n"):
            result_text += "\n"
        if result_text and not result_text.endswith("\n\n"):
            result_text += "\n"
        result_text += "".join(append)
    result = result_text.encode()
    if len(result) > LIMIT:
        raise SetupError("merged config exceeds 1 MiB bound")
    if _toml(result, "merged config") != expected:
        raise SetupError("bounded TOML merge could not prove the intended semantics; integrate manually")
    return result


def _guard_entry(asset: dict[str, Any]) -> tuple[str, Any]:
    hooks = asset.get("hooks")
    if not isinstance(hooks, dict):
        raise SetupError("package hooks JSON lacks hooks object")
    found: list[tuple[str, Any]] = []
    for event, entries in hooks.items():
        if isinstance(entries, list):
            for entry in entries:
                if _contains_guard(entry):
                    found.append((event, entry))
    if len(found) != 1:
        raise SetupError("package hooks JSON must contain exactly one guard entry")
    return found[0]


def _contains_guard(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    candidates = entry.get("hooks")
    if not isinstance(candidates, list):
        return False
    return any(isinstance(item, dict) and isinstance(item.get("command"), str)
               and "delegation_guard.py" in item["command"] for item in candidates)


def merge_hooks(existing_bytes: bytes, required_bytes: bytes) -> bytes:
    existing = _json_object(existing_bytes, "existing hooks")
    required = _json_object(required_bytes, "package hooks")
    event, guard = _guard_entry(required)
    hooks = existing.get("hooks")
    if hooks is None:
        hooks = {}
        existing["hooks"] = hooks
    if not isinstance(hooks, dict):
        raise SetupError("existing hooks JSON has non-object hooks")
    mentions: list[tuple[str, Any]] = []
    for existing_event, entries in hooks.items():
        if not isinstance(entries, list):
            raise SetupError(f"existing hooks JSON has non-list {existing_event} hooks")
        mentions.extend((existing_event, entry) for entry in entries if _contains_guard(entry))
    if len(mentions) > 1 or (mentions and mentions[0] != (event, guard)):
        raise SetupError("ambiguous or changed delegation guard hook; integrate manually")
    if mentions:
        return existing_bytes
    entries = hooks.setdefault(event, [])
    if not isinstance(entries, list):
        raise SetupError(f"existing hooks JSON has non-list {event} hooks")
    entries.append(copy.deepcopy(guard))
    return json.dumps(existing, indent=2, ensure_ascii=False).encode() + b"\n"


def managed_agents(existing: bytes | None, body: bytes) -> bytes:
    body_text = _utf8(body, "package AGENTS body").strip("\n")
    block = f"{BEGIN}\n{body_text}\n{END}\n"
    if existing is None:
        return block.encode()
    text = _utf8(existing, "existing AGENTS.md")
    begins, ends = text.count(BEGIN), text.count(END)
    if begins or ends:
        if begins != 1 or ends != 1:
            raise SetupError("malformed managed AGENTS block")
        start = text.index(BEGIN)
        end = text.index(END)
        if end < start:
            raise SetupError("malformed managed AGENTS block")
        finish = end + len(END)
        current = text[start:finish]
        if current != block.rstrip("\n"):
            raise SetupError("changed managed AGENTS block; integrate manually")
        return existing
    suffix = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return (text + suffix + block).encode()


def asset_bytes(relative: Path) -> bytes:
    path = PROJECT_ASSETS / relative
    _safe_dir(path.parent, ASSETS, create_ok=False)
    value = read_file(path)
    assert value is not None
    return value


def validate_project_root(root_arg: str) -> Path:
    root = Path(root_arg)
    if not root.is_absolute():
        raise SetupError("--project must be an absolute Git root")
    if root.is_symlink() or not root.is_dir():
        raise SetupError("--project must be a real Git-root directory")
    try:
        git_root = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                                  check=True, capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise SetupError("--project must be an existing Git root") from error
    if Path(git_root).resolve() != root.resolve():
        raise SetupError("--project must name the Git root, not a subdirectory")
    return root.resolve()


def plan_setup(root: Path) -> list[Change]:
    """Return all writes, or raise before any filesystem mutation."""
    changes: list[Change] = []
    for relative in CONTROL_FILES:
        source = asset_bytes(relative)
        if relative == Path(".codex/delegation-guard.json"):
            validate_flag(source, str(PROJECT_ASSETS / relative))
        elif relative == Path(".codex/delegation-policy.json"):
            validate_policy(source, str(PROJECT_ASSETS / relative))
        target = root / relative
        _safe_dir(target.parent, root, create_ok=True)
        before = read_file(target, missing_ok=True)
        if relative == Path(".codex/config.toml") and before is not None:
            after = merge_toml(before, source)
            reason = "merge missing required config fields"
        elif relative == Path(".codex/hooks.json") and before is not None:
            after = merge_hooks(before, source)
            reason = "append the guard hook"
        elif relative == Path(".codex/delegation-guard.json") and before is not None:
            validate_flag(before, str(target))
            after, reason = before, "preserve existing guard flag"
        elif relative == Path(".codex/delegation-policy.json") and before is not None:
            validate_policy(before, str(target))
            after, reason = before, "preserve existing allowed-model policy"
        else:
            after, reason = source, "install package asset"
            if before is not None and before != source:
                raise SetupError(f"conflicting owned file: {target}")
        if len(after) > LIMIT:
            raise SetupError(f"planned output exceeds 1 MiB bound: {target}")
        if before != after:
            changes.append(Change(target, after, before, reason))

    body = read_file(ASSETS / "AGENTS.md")
    assert body is not None
    target = root / "AGENTS.md"
    _safe_dir(target.parent, root, create_ok=True)
    before = read_file(target, missing_ok=True)
    after = managed_agents(before, body)
    if len(after) > LIMIT:
        raise SetupError(f"planned output exceeds 1 MiB bound: {target}")
    if before != after:
        changes.append(Change(target, after, before, "append managed Aperture guidance"))
    return changes


def _write_atomic(path: Path, content: bytes) -> None:
    mode = None
    if path.exists() or path.is_symlink():
        _not_link_regular(path)
        mode = path.stat().st_mode & 0o777
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".aperture-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _acquire_lock(root: Path) -> tuple[int, Path, tuple[int, int]]:
    """Acquire a root-local cooperative lock without writing Git metadata."""
    lock = root / ".aperture-agent-system.setup.lock"
    _safe_dir(lock.parent, root, create_ok=True)
    if lock.exists() or lock.is_symlink():
        if lock.is_symlink():
            raise SetupError("refusing symlink setup lock")
        raise SetupError("setup lock already exists; another setup may be running or remove a stale lock manually")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock, flags, 0o600)
    except FileExistsError as error:
        raise SetupError("setup lock already exists; another setup may be running or remove a stale lock manually") from error
    except OSError as error:
        raise SetupError("could not acquire a safe root setup lock") from error
    info = os.fstat(descriptor)
    return descriptor, lock, (info.st_dev, info.st_ino)


def _remove_owned_lock(lock: Path, identity: tuple[int, int]) -> None:
    try:
        info = lock.lstat()
        if (info.st_dev, info.st_ino) == identity and lock.is_file() and not lock.is_symlink():
            lock.unlink()
    except FileNotFoundError:
        return


def apply_changes(root: Path, changes: list[Change]) -> None:
    """Recheck then apply planned writes; restore only writes still ours on failure."""
    if not changes:
        return
    descriptor, lock_path, identity = _acquire_lock(root)
    try:
        with os.fdopen(descriptor, "wb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            written: list[Change] = []
            try:
                for change in changes:
                    _safe_dir(change.target.parent, root, create_ok=True)
                    if read_file(change.target, missing_ok=True) != change.before:
                        raise SetupError(f"project changed after preview: {change.target}")
                    _safe_dir(change.target.parent, root, create_ok=True)
                    if read_file(change.target, missing_ok=True) != change.before:
                        raise SetupError(f"project changed immediately before write: {change.target}")
                    _write_atomic(change.target, change.content)
                    written.append(change)
            except Exception as error:
                if not written and isinstance(error, SetupError):
                    raise
                refused = False
                for change in reversed(written):
                    try:
                        _safe_dir(change.target.parent, root, create_ok=True)
                        if read_file(change.target, missing_ok=True) != change.content:
                            refused = True
                            continue
                        _safe_dir(change.target.parent, root, create_ok=True)
                        if change.before is None:
                            change.target.unlink()
                        else:
                            _write_atomic(change.target, change.before)
                    except Exception:
                        refused = True
                extra = "; rollback refused an intervening edit" if refused else ""
                raise SetupError(f"apply failed and attempted rollback{extra}") from error
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
    finally:
        _remove_owned_lock(lock_path, identity)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="absolute Git root to preview or configure")
    parser.add_argument("--apply", action="store_true", help="apply the fully preflighted setup")
    args = parser.parse_args(argv)
    try:
        root = validate_project_root(args.project)
        changes = plan_setup(root)
        action = "Apply" if args.apply else "Preview"
        if not changes:
            print(f"{action}: no changes.")
        else:
            print(f"{action}: {len(changes)} planned change(s):")
            for change in changes:
                print(f"- {change.target.relative_to(root)}: {change.reason}")
        if args.apply:
            apply_changes(root, changes)
            print("Applied safely.")
        return 0
    except SetupError as error:
        print(f"Setup refused: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Setup refused: an expected filesystem operation could not complete safely.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
