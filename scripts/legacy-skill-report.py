#!/usr/bin/env python3
"""legacy-skill-report.py — stale-pattern report over the skill catalog (advisory).

Scans skills/*/SKILL.md (and references/ where noted) for patterns left behind
by retired architecture: the XML result contract, the ingestion pipeline,
magic-number retry doctrine, mandatory Schema mutation, retired skill names,
absolutist "Iron Law" framing, over-broad triggers, and universal-template-
specific workflow names presented as universal rules. Also validates explicit
skill-to-skill references ("use/load/delegate to/route to `name`").

Advisory: warnings are a migration queue and never fail the build by default.
--strict turns any warning into a failure (for after a cleanup wave).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = BASE / "skills"

PATTERNS: list[tuple[str, str, str]] = [
    ("legacy-result-contract", r"<skill_result>",
     "unused XML result contract (no consumer; drop when touching the skill)"),
    ("legacy-ingestion", r"ingestion-index|ingestion-protocol|ingest one topic|learning-note",
     "legacy ingestion architecture (catalog is reference-first now)"),
    ("magic-retry", r"[Aa]fter (two|2|three|3) (consecutive )?(failures|failed fixes|retries)",
     "magic-number retry doctrine (prefer hypothesis-invalidation)"),
    ("mandatory-schema", r"must use the Schema loop|Schema loop is mandatory|before any mutation, run the Schema loop",
     "mandatory Schema mutation policy (Schema is opt-in)"),
    ("retired-skill", r"workflow-lifecycle|codebase-driven-development|codegraph-context|codegraphcontext|five-source",
     "retired skill/tool reference"),
    ("iron-law-absolutism", r"^## The Iron Law\s*$",
     "absolutist Iron Law framing (prefer evidence rules)"),
    ("broad-trigger", r"^description:.*[Uu]se when (starting implementation|starting a coding task|starting any)",
     "over-broad trigger (competes with the normal development loop)"),
    ("ut-specific-tooling", r"pr-quality\.yml|security-audit\.yml",
     "universal-template workflow name; keep repo-specific facts in repo config or mark as example"),
    ("self-quiz", r"^## Self-Quiz\s*$", "legacy self-quiz section"),
]

PROVIDERS = ("Codebase Memory", "Fovea", "JetBrains", "Context7", "OpenViking")

# Backticked identifiers that are not skills: Veda personas, DOM attributes.
REFERENCE_ALLOWLIST = {
    "context-curator", "repo-scout", "frontend-auditor",
    "navigator-plan", "data-testid", "data-anonymize",
}
ROUTER_OWNER = "evidence-router"

# The archived awesome-guidelines library legitimately contains ingestion
# vocabulary in its references; only its SKILL.md is reported.
INGESTION_SKIP = "skills/awesome-guidelines/references/"


def iter_skill_files() -> list[Path]:
    files: list[Path] = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        sm = d / "SKILL.md"
        if sm.is_file():
            files.append(sm)
        refs = d / "references"
        if refs.is_dir():
            files.extend(sorted(refs.glob("*.md")))
    return files


def rel(p: Path) -> str:
    return str(p.relative_to(BASE))


def scan_patterns(files: list[Path]) -> list[str]:
    warns: list[str] = []
    for f in files:
        r = rel(f)
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for cid, pattern, note in PATTERNS:
                if cid == "legacy-ingestion" and r.startswith(INGESTION_SKIP):
                    continue
                if cid == "legacy-ingestion" and "awesome-guidelines/references/" in line:
                    continue  # capsule path citations are load-bearing content pointers
                if re.search(pattern, line):
                    warns.append(f"[{cid}] {r}:{i}: {note}")
    return warns


def scan_duplicate_evidence_routing(files: list[Path]) -> list[str]:
    warns: list[str] = []
    for f in files:
        if not f.name == "SKILL.md" or f.parent.name == ROUTER_OWNER:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "|" not in line:
                continue
            hits = sum(1 for p in PROVIDERS if p in line)
            if hits >= 2:
                warns.append(
                    f"[duplicate-evidence-routing] {rel(f)}:{i}: routing table names "
                    f"{hits} evidence providers; evidence-router owns source selection")
    return warns


def _non_skill_targets() -> set[str]:
    """Stems that legitimately resolve outside skills/: repo references/ capsules
    and scripts."""
    stems: set[str] = set()
    for p in (BASE / "references").glob("*.md"):
        stems.add(p.stem)
    for p in (BASE / "scripts").glob("*.py"):
        stems.add(p.stem)
    return stems


def scan_references(files: list[Path]) -> list[str]:
    warns: list[str] = []
    seen: set[tuple[str, str]] = set()
    stems = _non_skill_targets()
    capsule_stems: set[str] = set()
    for p in SKILLS.glob("*/references/*.md"):
        capsule_stems.add(p.stem)
    for f in files:
        if f.name != "SKILL.md":
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(
                    r"(?:use|load|delegate to|route to|via|per)\s+`([a-z0-9][a-z0-9-]+)`",
                    line, re.I):
                name = m.group(1)
                if "." in name or "-" not in name or name.startswith("x-"):
                    continue
                if name != name.lower():
                    continue
                if (SKILLS / name).is_dir() or name in stems or name in capsule_stems \
                        or name in REFERENCE_ALLOWLIST:
                    continue
                key = (f.parent.name, name)
                if key in seen:
                    continue
                seen.add(key)
                warns.append(
                    f"[skill-reference] {rel(f)}:{i}: explicit reference does not "
                    f"resolve to a skill: {name}")
    return warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on any warning (post-cleanup hardening)")
    args = ap.parse_args()
    files = iter_skill_files()
    warns = scan_patterns(files) + scan_duplicate_evidence_routing(files) + scan_references(files)
    print(f"Legacy skill migration report — {len(files)} files scanned, "
          f"{len(warns)} warnings")
    for w in warns:
        print(f"  {w}")
    if not warns:
        print("  no legacy patterns found")
    if args.strict and warns:
        print("--strict: failing on warnings", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
