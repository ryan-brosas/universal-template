#!/usr/bin/env python3
"""pr-metadata.py - the single deterministic parser for PR/commit titles.

One parser serves every consumer: local validation, the pr-title CI check,
PR type/breaking labels, and release-note categories. The grammar is imported
from scripts/conventional-commit.py so there is exactly one implementation.

Usage:
  pr-metadata.py validate --title "feat(x): desc"   # exit 0/1 + reasons
  pr-metadata.py labels  --title "fix!: desc"       # space-separated labels
  pr-metadata.py json    --title "..."              # structured metadata
  pr-metadata.py --selftest                         # golden cases
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _load_conventional_commit():
    spec = importlib.util.spec_from_file_location(
        "conventional_commit",
        str(Path(__file__).with_name("conventional-commit.py")),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


cc = _load_conventional_commit()

# PR-title type -> label. Types without a label (style, revert, release) map
# deliberately to nothing rather than to a wrong category.
TYPE_LABELS = {
    "feat": "type:feature",
    "fix": "type:bug",
    "docs": "type:docs",
    "refactor": "type:refactor",
    "perf": "type:performance",
    "test": "type:test",
    "chore": "type:chore",
    "ci": "type:ci",
    "build": "type:build",
}
BREAKING_LABEL = "breaking-change"


def parse(title: str) -> dict | None:
    m = cc.CONV_PAT.match(title.strip())
    if not m:
        return None
    prefix = title.strip().split(":", 1)[0]
    return {
        "type": m.group("type"),
        "scope": m.group("scope"),
        "breaking": prefix.endswith("!"),
        "description": m.group("desc"),
    }


def validate(title: str) -> list[str]:
    return cc.check_subject(title)


def labels(title: str) -> list[str]:
    p = parse(title)
    if p is None:
        return []
    out = []
    if p["type"] in TYPE_LABELS:
        out.append(TYPE_LABELS[p["type"]])
    if p["breaking"]:
        out.append(BREAKING_LABEL)
    return out


SELFTEST = [
    ("feat(routing): add cold skill discovery", ["type:feature"], []),
    ("fix!: change bootstrap contract", ["type:bug", "breaking-change"], []),
    ("ci(deps): bump actions/checkout", ["type:ci"], []),
    ("style: reformat", [], []),
    # Unparseable: no labels, validation error.
    ("update stuff", [], ["not conventional"]),
    # Parseable but invalid: labels still derive; validation blocks the merge.
    ("feat: Add a capital", ["type:feature"], ["capital"]),
    ("feat(x): ends with period.", ["type:feature"], ["period"]),
]


def selftest() -> int:
    ok = True
    for title, want_labels, error_fragments in SELFTEST:
        got = labels(title)
        errs = validate(title)
        if got != want_labels or any(f not in " ".join(errs) for f in error_fragments):
            print(f"FAIL {title!r}: labels={got} errors={errs}")
            ok = False
    print("pr-metadata selftest: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", nargs="?", choices=("validate", "labels", "json"))
    ap.add_argument("--title")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if not args.command or args.title is None:
        ap.error("command and --title are required (or pass --selftest)")
    if args.command == "validate":
        errs = validate(args.title)
        if errs:
            print(f"::error::PR title {args.title!r} is not conventional: " + "; ".join(errs))
            print("Use '<type>(<scope>): <desc>' with a lowercase description.")
            sys.exit(1)
        print(f"PR title is conventional: {parse(args.title)}")
        return 0
    if args.command == "labels":
        print(" ".join(labels(args.title)))
        return 0
    print(json.dumps(parse(args.title), indent=2))
    return 0


if __name__ == "__main__":
    main()
