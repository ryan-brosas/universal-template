#!/usr/bin/env python3
"""Guard the template's context architecture against retired systems returning.

Retired by the simplification refactor: Codebase Memory, DeepWiki, the
foundations knowledge store, the `awesome-guidelines` capsule library, the
`api-design-practices` compatibility alias, and OpenViking. Code context now
comes from current source, Sourcebot, GitHub discovery, and official docs.

Run with --selftest to check the matcher, or with no arguments to scan every
tracked file. Exit status is nonzero when a retired reference is found.
"""

import re
import subprocess
import sys

PATTERNS = [
    r"awesome-guidelines",
    r"api-design-practices",
    r"codebase-memory",
    r"deepwiki",
    r"knowledge/foundations",
    r"foundation-pack",
    r"openviking",
]

MATCHER = re.compile("|".join(PATTERNS), re.IGNORECASE)
ALLOWLIST = {"scripts/check-retired-paths.py", "CONTRIBUTING.md"}


def tracked_files():
    out = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, check=True
    ).stdout
    return [f for f in out.split("\0") if f]


def scan():
    hits = []
    for path in tracked_files():
        if path in ALLOWLIST:
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if MATCHER.search(line):
                hits.append(f"{path}:{number}: {line.strip()}")
    return hits


def selftest():
    assert MATCHER.search("see knowledge/foundations/turso")
    assert MATCHER.search("deepwiki-mcp")
    assert MATCHER.search("openviking")
    assert not MATCHER.search("foundational principles")
    assert not MATCHER.search("a solid foundation")
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    found = scan()
    if found:
        print("retired architecture references found:")
        print("\n".join(found))
        raise SystemExit(1)
    print("no retired architecture references")
