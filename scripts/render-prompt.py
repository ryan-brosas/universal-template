#!/usr/bin/env python3
"""Render one canonical prompt for hosts without native prompt shortcuts."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PROMPTS = BASE / "prompts"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", help="prompt filename without .md")
    parser.add_argument("arguments", nargs="*", help="arguments passed to $ARGUMENTS")
    args = parser.parse_args()

    files = sorted(PROMPTS.glob("*.md"))
    if args.name is None:
        for path in files:
            print(path.stem)
        return 0
    if not NAME_RE.fullmatch(args.name):
        parser.error("prompt name must use lowercase letters, numbers, and hyphens")
    path = PROMPTS / f"{args.name}.md"
    if not path.is_file():
        parser.error(f"unknown prompt: {args.name}")

    values = args.arguments
    rendered = path.read_text(encoding="utf-8")
    joined = " ".join(values)
    rendered = rendered.replace("$ARGUMENTS", joined).replace("$@", joined)
    for index in range(len(values), 0, -1):
        rendered = rendered.replace(f"${index}", values[index - 1])
    sys.stdout.write(rendered)
    if rendered and not rendered.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
