#!/usr/bin/env python3
"""Parse the exact pull-request title protocol used by repository automation."""
from __future__ import annotations

import argparse
import json
import re
import sys

ALLOWED_TYPES = {
    "feat", "fix", "docs", "style", "refactor", "perf", "test", "chore",
    "ci", "build", "revert", "release", "security", "deps",
}
TYPE_LABELS = {
    "feat": "type:feature", "fix": "type:bug", "docs": "type:docs",
    "refactor": "type:refactor", "perf": "type:performance", "test": "type:test",
    "chore": "type:chore", "ci": "type:ci", "build": "type:build",
    "security": "type:security", "deps": "type:dependencies",
}
BREAKING_LABEL = "breaking-change"
TITLE_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9_-]+)\))?(?P<breaking>!)?:\s*(?P<description>.+)$"
)


def parse(title: str) -> dict | None:
    match = TITLE_RE.fullmatch(title.strip())
    if not match:
        return None
    return {
        "type": match.group("type"), "scope": match.group("scope"),
        "breaking": bool(match.group("breaking")),
        "description": match.group("description"),
    }


def validate(title: str) -> list[str]:
    parsed = parse(title)
    if parsed is None:
        return ["not conventional; expected '<type>(<scope>): <description>'"]
    errors: list[str] = []
    if parsed["type"] not in ALLOWED_TYPES:
        errors.append(f"unknown type {parsed['type']!r}")
    return errors


def labels(title: str) -> list[str]:
    parsed = parse(title)
    if parsed is None:
        return []
    result = [TYPE_LABELS[parsed["type"]]] if parsed["type"] in TYPE_LABELS else []
    if parsed["breaking"]:
        result.append(BREAKING_LABEL)
    return result


def selftest() -> int:
    cases = (
        ("feat(routing): add cold skill discovery", ["type:feature"], True),
        ("fix!: change bootstrap contract", ["type:bug", "breaking-change"], True),
        ("style: reformat", [], True),
        ("security(auth): reject leaked tokens", ["type:security"], True),
        ("deps: pin context server", ["type:dependencies"], True),
        ("update stuff", [], False),
        ("feat: Add a capital", ["type:feature"], True),
        ("fix(parser): End with a period.", ["type:bug"], True),
        ("fix(parser):   ", [], False),
    )
    ok = True
    for title, expected_labels, valid in cases:
        if labels(title) != expected_labels or (not validate(title)) != valid:
            print(f"FAIL {title!r}")
            ok = False
    print("pr-metadata selftest: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("validate", "labels", "json"))
    parser.add_argument("--title")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.command or args.title is None:
        parser.error("command and --title are required (or pass --selftest)")
    if args.command == "validate":
        errors = validate(args.title)
        if errors:
            print(f"::error::PR title {args.title!r} is invalid: " + "; ".join(errors))
            return 1
        print(f"PR title is conventional: {parse(args.title)}")
        return 0
    if args.command == "labels":
        print(" ".join(labels(args.title)))
        return 0
    print(json.dumps(parse(args.title), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
