#!/usr/bin/env python3
"""Catalog quality gate — anti-slop structure for skills/essentials/templates.

Ported from pi-template quality-gate.py for the absorbed ~/.agents layout:
- every skill dir has SKILL.md; name matches folder
- no duplicate skill names
- essentials present and indexed in essentials/README.md
- templates inventory matches templates/ on disk
- near-duplicate descriptions reported as warnings (non-blocking)

Hard failures exit 1. Warnings print but do not fail.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SKILLS = BASE / "skills"
ESSENTIALS = BASE / "essentials"
TEMPLATES = BASE / "templates"
INVENTORY = BASE / "references" / "templates-inventory.md"

errors: list[str] = []
warnings: list[str] = []

ESSENTIAL_FILES = [
    "operating-philosophy.md",
    "guiding-small-model.md",
    "steer-outcomes-not-behavior.md",
    "stack-your-leverage.md",
    "enforce-code-quality-mechanically.md",
    "how-to-build-good-tests.md",
    "objectives.md",
    "README.md",
]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    raw = text[4:end] if text.startswith("---\n") else text[3:end]
    fm: dict[str, str] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        j = i + 1
        extra: list[str] = []
        while j < len(lines) and not re.match(r"^[A-Za-z0-9_-]+:\s*", lines[j]):
            extra.append(lines[j])
            j += 1
        val = " ".join([val] + [e.strip() for e in extra]).strip()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        fm[key] = val
        i = j
    return fm


def collect_skills() -> dict[str, dict]:
    skills: dict[str, dict] = {}
    if not SKILLS.is_dir():
        errors.append("skills/ missing")
        return skills
    for entry in sorted(SKILLS.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"missing SKILL.md: skills/{entry.name}")
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        name = fm.get("name", entry.name)
        desc = fm.get("description", "")
        if name != entry.name:
            errors.append(f"name/folder mismatch: skills/{entry.name} name={name!r}")
        if name in skills:
            errors.append(f"duplicate skill name: {name}")
        skills[name] = {"path": str(skill_md), "desc": desc, "dir": str(entry)}
    return skills


def check_essentials() -> None:
    for ef in ESSENTIAL_FILES:
        if not (ESSENTIALS / ef).is_file():
            errors.append(f"missing essential doc: {ef}")
    readme = (ESSENTIALS / "README.md").read_text(encoding="utf-8") if (ESSENTIALS / "README.md").is_file() else ""
    for ef in ESSENTIAL_FILES:
        if ef != "README.md" and ef not in readme:
            errors.append(f"essential not indexed in README: {ef}")


def check_templates_inventory() -> None:
    if not INVENTORY.is_file():
        errors.append("missing references/templates-inventory.md")
        return
    inv = INVENTORY.read_text(encoding="utf-8")
    on_disk = sorted(
        p.name
        for p in TEMPLATES.iterdir()
        if p.is_file() and not p.name.startswith(".")
    )
    for name in on_disk:
        # source.yml is an inspo ledger template; inventory may list it or omit —
        # require every non-source template to be named in the inventory body.
        if name == "source.yml":
            continue
        if name not in inv:
            errors.append(f"template not listed in inventory: {name}")
    # Count claimed in inventory header vs format templates excluding source.yml
    claimed = re.search(r"(\d+)\s+CLI-neutral format templates", inv)
    expected = len([n for n in on_disk if n != "source.yml"])
    if claimed:
        n = int(claimed.group(1))
        if n != expected:
            errors.append(
                f"templates inventory count {n} != on-disk format templates {expected} "
                f"(excluding source.yml)"
            )


def near_duplicate_warnings(skills: dict[str, dict]) -> None:
    descs = [(n, i["desc"].lower()) for n, i in skills.items() if i["desc"]]
    for i in range(len(descs)):
        for j in range(i + 1, len(descs)):
            n1, d1 = descs[i]
            n2, d2 = descs[j]
            shorter = min(len(d1), len(d2))
            if shorter < 40:
                continue
            common = 0
            for k in range(min(shorter, 80)):
                if d1[k] == d2[k]:
                    common += 1
                else:
                    break
            if common > 0.7 * min(shorter, 80):
                warnings.append(f"near-duplicate descriptions: {n1} ~ {n2} (prefix {common} chars)")


def main() -> int:
    skills = collect_skills()
    check_essentials()
    check_templates_inventory()
    near_duplicate_warnings(skills)

    if errors:
        print("CATALOG QUALITY FAILURES:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"CATALOG QUALITY OK: {len(skills)} skills, {len(ESSENTIAL_FILES)} essentials")
    for w in warnings[:40]:
        print(f"  (warn) {w}")
    if len(warnings) > 40:
        print(f"  (warn) ... {len(warnings)} total warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
