#!/usr/bin/env python3
"""Validate exact skill metadata, names, visibility, and local references.

This gate deliberately does not judge prose, usefulness, overlap, routing, or
section structure. Those decisions belong to model review.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = Path(os.environ.get("SKILLS_ROOT", str(BASE / "skills")))
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
INVOCATIONS = {"entry", "internal", "manual", "vendor"}
FOUNDATION_KIND = "foundation"
LEGACY_FOUNDATIONS = BASE / ("foundation" + "-pack")


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


def validate_foundation_index(skill: Path) -> list[str]:
    errors: list[str] = []
    references = skill.parent / "references"
    index = references / "index.md"
    if not index.is_file():
        return [f"{skill}: foundation references/index.md missing"]
    text = index.read_text(encoding="utf-8")
    linked = set(re.findall(r"\]\((?:\./)?([A-Za-z0-9][A-Za-z0-9._-]*\.md)\)", text))
    on_disk = {path.name for path in references.glob("*.md") if path.name != "index.md"}
    for name in sorted(on_disk - linked):
        errors.append(f"{index}: reference file absent from inventory: {name}")
    for name in sorted(linked - on_disk):
        errors.append(f"{index}: inventory target missing: {name}")
    return errors


def validate_skill(skill: Path, require_invocation: bool = True) -> tuple[str | None, list[str]]:
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

        kind = metadata.get("kind")
        foundation_name = bool(name and name.endswith("-foundation"))
        if foundation_name and kind != FOUNDATION_KIND:
            errors.append(f"{skill}: *-foundation requires kind: foundation")
        if kind == FOUNDATION_KIND and not foundation_name:
            errors.append(f"{skill}: kind: foundation requires a *-foundation name")
        if kind not in {None, FOUNDATION_KIND}:
            errors.append(f"{skill}: unsupported kind: {kind!r}")
        if kind == FOUNDATION_KIND:
            if invocation != "manual":
                errors.append(f"{skill}: foundation invocation must be manual")
            if not hidden:
                errors.append(f"{skill}: foundations must disable model invocation")
            errors.extend(validate_foundation_index(skill))
    errors.extend(referenced_files(skill, text))
    return name, errors


def validate_tree(root: Path, require_invocation: bool = True, ignored: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    if not root.is_dir():
        return [f"required directory missing: {root}"]
    ignored = ignored or set()
    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith(".") or directory.name in ignored:
            continue
        if directory.is_symlink():
            errors.append(f"{directory}: skill directories must not be symlinks")
            continue
        skill = directory / "SKILL.md"
        if skill.is_symlink():
            errors.append(f"{skill}: SKILL.md must not be a symlink")
            continue
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


def selftest() -> int:
    with tempfile.TemporaryDirectory(prefix="skill-validator-") as temp:
        root = Path(temp) / "skills"
        valid = root / "demo-foundation"
        (valid / "references").mkdir(parents=True)
        (valid / "references" / "capsule.md").write_text("evidence\n", encoding="utf-8")
        (valid / "references" / "index.md").write_text(
            "- [`capsule.md`](./capsule.md)\n", encoding="utf-8"
        )
        valid_text = (
            "---\nname: demo-foundation\ndescription: cold evidence\n"
            "kind: foundation\ninvocation: manual\n"
            "disable-model-invocation: true\n---\n"
            "# Demo\n\nSee `references/index.md`.\n"
        )
        (valid / "SKILL.md").write_text(valid_text, encoding="utf-8")
        if validate_tree(root):
            print("selftest: valid foundation rejected", file=sys.stderr)
            return 1
        cases = [
            (
                valid_text.replace("invocation: manual", "invocation: entry"),
                {"entry invocation contradicts hidden visibility", "foundation invocation must be manual"},
            ),
            (valid_text.replace("kind: foundation\n", ""), {"*-foundation requires kind: foundation"}),
            (
                valid_text.replace("disable-model-invocation: true", "disable-model-invocation: false"),
                {"manual invocation requires hidden visibility", "foundations must disable model invocation"},
            ),
        ]
        for bad, expected in cases:
            (valid / "SKILL.md").write_text(bad, encoding="utf-8")
            errors = validate_tree(root)
            if not all(any(needle in error for error in errors) for needle in expected):
                print(f"selftest: foundation invariants not caught: {errors}", file=sys.stderr)
                return 1
    print("SKILL VALIDATOR SELFTEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    ignored = git_ignored_dirs(SKILLS) if SKILLS == BASE / "skills" else set()
    errors = validate_tree(SKILLS, True, ignored)
    if SKILLS == BASE / "skills" and (
        LEGACY_FOUNDATIONS.exists() or LEGACY_FOUNDATIONS.is_symlink()
    ):
        errors.append("retired foundation directory must not exist (including symlinks)")
    for error in errors:
        print(f"FAIL  {error}")
    print(f"SKILL CONTRACTS: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
