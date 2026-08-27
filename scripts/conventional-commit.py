#!/usr/bin/env python3
"""Conventional-commit check for subjects on the branch range.

Ported from pi-template. Format: <type>(<scope>): <description>
Types align with AGENTS.md: feat, fix, docs, chore, refactor, test (+ ci/build/perf/style/revert/release).

When CHECK_RANGE is set (e.g. origin/main..HEAD), only those commits are checked.
Otherwise the last 20 commits on HEAD are checked. Merge commits are skipped.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

ALLOWED_TYPES = {
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "chore",
    "ci",
    "build",
    "revert",
    "release",
}

CONV_PAT = re.compile(
    r"^(?P<type>[a-z]+)(\((?P<scope>[a-z0-9_\-]+)\))?!?:\s*(?P<desc>.+)$"
)


def check_subject(subject: str) -> list[str]:
    v: list[str] = []
    m = CONV_PAT.match(subject.strip())
    if not m:
        return [f"not conventional (want '<type>(<scope>): <desc>', got {subject.strip()!r})"]
    if m.group("type") not in ALLOWED_TYPES:
        v.append(f"unknown type '{m.group('type')}' (allowed: {sorted(ALLOWED_TYPES)})")
    desc = m.group("desc")
    if desc and desc[0].isupper():
        v.append("description should not start with a capital letter")
    if desc.endswith("."):
        v.append("description should not end with a period")
    return v


def subjects() -> list[str]:
    rng = os.environ.get("CHECK_RANGE", "")
    if rng:
        cmd = ["git", "log", "--pretty=%s", rng]
    else:
        cmd = ["git", "log", "--pretty=%s", "-20"]
    out = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, check=False)
    return [line for line in out.stdout.splitlines() if line.strip()]


def main() -> int:
    errors: list[str] = []
    for line in subjects():
        if line.startswith("Merge ") or line.startswith("Revert "):
            continue
        for v in check_subject(line):
            errors.append(f"commit {line!r}: {v}")
    if errors:
        print("CONVENTIONAL COMMIT VIOLATIONS:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("CONVENTIONAL COMMITS OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
