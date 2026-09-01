#!/usr/bin/env python3
"""reference-retrieval-fixture.py — policy proxy for reference discovery wiring.

Checks that policy surfaces (project-bootstrap inventory, RDD retrieval
description) exist so agents can notice project-local references without
being told explicitly. Not a full agent eval harness.

Exit 0 when fixture + policy triggers are present.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FIXTURE = BASE / "scripts" / "fixtures" / "reference-retrieval-project"


def check_policy_triggers() -> list[str]:
    errors: list[str] = []
    bootstrap = (BASE / "skills/project-bootstrap/SKILL.md").read_text(encoding="utf-8")
    if "reference/web/" not in bootstrap or "filesystem listing" not in bootstrap:
        errors.append("project-bootstrap missing bounded reference inventory")
    rdd = (BASE / "skills/reference-driven-development/SKILL.md").read_text(encoding="utf-8")
    if "description:" not in rdd:
        errors.append("reference-driven-development missing description")
    else:
        head = rdd.split("---", 2)[1] if rdd.startswith("---") else ""
        if "reference/web/" not in head and "project-local" not in head:
            errors.append("RDD description missing existing-reference retrieval trigger")
    evidence = (BASE / "skills/evidence-router/SKILL.md").read_text(encoding="utf-8")
    if "reference/web/" not in evidence or "Evidence priority" not in evidence:
        errors.append("evidence-router missing reference priority")
    return errors


def check_fixture_layout() -> list[str]:
    errors: list[str] = []
    required = (
        FIXTURE / "src" / "components" / "Dashboard.tsx",
        FIXTURE / "reference" / "good-backend" / "README.md",
        FIXTURE / "reference" / "web" / "good-ui" / "REFERENCE.md",
        FIXTURE / "reference" / "web" / "good-ui" / "manifest.json",
    )
    for path in required:
        if not path.is_file():
            errors.append(f"fixture missing {path.relative_to(BASE)}")
    return errors


def selftest() -> int:
    layout_errors = check_fixture_layout()
    if layout_errors:
        print("FAIL fixture layout incomplete:")
        for e in layout_errors:
            print(f"  {e}")
        return 1
    print("PASS reference-retrieval fixture layout")
    policy_errors = check_policy_triggers()
    if policy_errors:
        print("FAIL policy triggers incomplete:")
        for e in policy_errors:
            print(f"  {e}")
        return 1
    print("PASS reference-retrieval policy triggers")
    print("reference-retrieval-fixture selftest: PASS")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    errors = check_fixture_layout() + check_policy_triggers()
    for e in errors:
        print(f"FAIL  {e}")
    print(f"REFERENCE RETRIEVAL FIXTURE: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
