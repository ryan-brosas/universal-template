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
PLACEHOLDER_RE = re.compile(r"\$(?:ARGUMENTS|@|[1-9]\d*)")


def render_text(text: str, values: list[str]) -> str:
    """Expand placeholders in the source text without rescanning inserted values."""
    joined = " ".join(values)

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in {"$ARGUMENTS", "$@"}:
            return joined
        index = int(token[1:])
        return values[index - 1] if index <= len(values) else token

    return PLACEHOLDER_RE.sub(replace, text)


def selftest(files: list[Path]) -> int:
    if not files:
        print("selftest: no canonical prompts found", file=sys.stderr)
        return 1
    cases = (
        ("$ARGUMENTS", ["first", "second"], "first second"),
        ("$@ / $1 / $2", ["one", "two"], "one two / one / two"),
        ("keep $1 and $2", ["literal $1", "literal $2"], "keep literal $1 and literal $2"),
        ("$1/$2/$3", ["one", "two"], "one/two/$3"),
    )
    for source, values, expected in cases:
        if render_text(source, values) != expected:
            print(f"selftest: placeholder expansion drift for {source!r}", file=sys.stderr)
            return 1
    for path in files:
        if "$ARGUMENTS" in render_text(path.read_text(encoding="utf-8"), ["probe"]):
            print(f"selftest: canonical placeholder not rendered: {path}", file=sys.stderr)
            return 1
    print(f"PROMPT RENDERER SELFTEST PASS ({len(files)} prompts; single-pass expansion)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", help="prompt filename without .md")
    parser.add_argument("arguments", nargs="*", help="arguments passed to $ARGUMENTS")
    parser.add_argument("--selftest", action="store_true", help="run placeholder and canonical-prompt probes")
    args = parser.parse_args()

    files = sorted(PROMPTS.glob("*.md"))
    if args.selftest:
        return selftest(files)
    if args.name is None:
        for path in files:
            print(path.stem)
        return 0
    if not NAME_RE.fullmatch(args.name):
        parser.error("prompt name must use lowercase letters, numbers, and hyphens")
    path = PROMPTS / f"{args.name}.md"
    if not path.is_file():
        parser.error(f"unknown prompt: {args.name}")

    rendered = render_text(path.read_text(encoding="utf-8"), args.arguments)
    sys.stdout.write(rendered)
    if rendered and not rendered.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
