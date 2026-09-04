#!/usr/bin/env python3
"""Validate exact skill metadata, names, visibility, and local references.

This gate deliberately does not judge prose, usefulness, overlap, routing, or
section structure. Those decisions belong to model review.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = Path(os.environ.get("SKILLS_ROOT", str(BASE / "skills")))
FOUNDATIONS = BASE / "foundation-pack"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INVOCATIONS = {"entry", "internal", "manual", "vendor"}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        result[key] = value
    return result


def git_ignored_dirs(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    names = [entry.name for entry in root.iterdir() if entry.is_dir()]
    if not names:
        return set()
    try:
        result = subprocess.run(
            ["git", "-C", str(root.parent), "check-ignore", "--stdin", "--no-index"],
            input="".join(f"{root.name}/{name}\n" for name in names),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return set()
    if result.returncode not in (0, 1):
        return set()
    return {line.rsplit("/", 1)[-1] for line in result.stdout.splitlines()}


def referenced_files(skill: Path, text: str) -> list[str]:
    errors: list[str] = []
    for relative in sorted(set(re.findall(r"`(references/[A-Za-z0-9][A-Za-z0-9._/-]*)`", text))):
        target = (skill.parent / relative).resolve()
        try:
            target.relative_to(skill.parent.resolve())
        except ValueError:
            errors.append(f"{skill}: reference escapes skill directory: {relative}")
            continue
        if not target.is_file():
            errors.append(f"{skill}: referenced file missing: {relative}")
    return errors


def validate_skill(skill: Path, require_invocation: bool) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    try:
        text = skill.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"{skill}: unreadable: {exc}"]
    metadata = parse_frontmatter(text)
    if not metadata:
        return None, [f"{skill}: frontmatter missing or unparseable"]
    name = metadata.get("name")
    if not name:
        errors.append(f"{skill}: name missing")
    elif not NAME_RE.fullmatch(name):
        errors.append(f"{skill}: invalid skill name: {name!r}")
    elif name != skill.parent.name:
        errors.append(f"{skill}: name {name!r} != directory {skill.parent.name!r}")
    if not metadata.get("description", "").strip():
        errors.append(f"{skill}: description missing")
    if require_invocation:
        invocation = metadata.get("invocation")
        if invocation not in INVOCATIONS:
            errors.append(
                f"{skill}: invocation must be one of {sorted(INVOCATIONS)}, got {invocation!r}"
            )
        raw_hidden = metadata.get("disable-model-invocation", "false").lower()
        if raw_hidden not in {"true", "false"}:
            errors.append(f"{skill}: disable-model-invocation must be true or false")
        hidden = raw_hidden == "true"
        if invocation == "entry" and hidden:
            errors.append(f"{skill}: entry invocation contradicts hidden visibility")
        if invocation in {"internal", "manual"} and not hidden:
            errors.append(f"{skill}: {invocation} invocation requires hidden visibility")
    errors.extend(referenced_files(skill, text))
    return name, errors


def validate_tree(root: Path, require_invocation: bool, ignored: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    if not root.is_dir():
        return [f"required directory missing: {root}"]
    ignored = ignored or set()
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith(".") or directory.name in ignored:
            continue
        if root == FOUNDATIONS and not directory.name.endswith("-foundation"):
            continue
        skill = directory / "SKILL.md"
        if not skill.is_file():
            errors.append(f"{directory}: SKILL.md missing")
            continue
        name, skill_errors = validate_skill(skill, require_invocation)
        errors.extend(skill_errors)
        if name in seen:
            errors.append(f"{skill}: duplicate skill name: {name}")
        elif name:
            seen.add(name)
    return errors


def main() -> int:
    ignored = git_ignored_dirs(SKILLS) if SKILLS == BASE / "skills" else set()
    errors = validate_tree(SKILLS, True, ignored)
    if SKILLS == BASE / "skills":
        errors.extend(validate_tree(FOUNDATIONS, False))
    for error in errors:
        print(f"FAIL  {error}")
    print(f"SKILL CONTRACTS: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
