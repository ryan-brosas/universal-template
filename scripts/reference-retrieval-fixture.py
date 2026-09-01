#!/usr/bin/env python3
"""leverage-discovery-fixture.py — behavioral proxy for reference + leverage discovery.

Checks policy wiring and deterministic search behavior so agents can discover
project-local references, hidden skills, and foundations without explicit user
prompts. Not a full live-agent eval harness.

Exit 0 when fixture layout, policy triggers, and ranked search behave.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PROJECT_FIXTURE = BASE / "scripts" / "fixtures" / "reference-retrieval-project"
LEVERAGE_FIXTURE = BASE / "scripts" / "fixtures" / "leverage-discovery"


def _load_skill_catalog():
    spec = importlib.util.spec_from_file_location(
        "skill_catalog", str(BASE / "scripts" / "skill-catalog.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_policy_triggers() -> list[str]:
    errors: list[str] = []
    bootstrap = (BASE / "skills/project-bootstrap/SKILL.md").read_text(encoding="utf-8")
    if "reference/web/" not in bootstrap or "filesystem listing" not in bootstrap:
        errors.append("project-bootstrap missing bounded reference inventory")
    rdd = (BASE / "skills/reference-driven-development/SKILL.md").read_text(encoding="utf-8")
    if rdd.startswith("---"):
        head = rdd.split("---", 2)[1]
        if "reference/web/" not in head and "project-local" not in head:
            errors.append("RDD description missing existing-reference retrieval trigger")
    evidence = (BASE / "skills/evidence-router/SKILL.md").read_text(encoding="utf-8")
    if "reference/web/" not in evidence or "Evidence priority" not in evidence:
        errors.append("evidence-router missing reference priority")
    if "search-leverage" not in evidence and "Reusable knowledge discovery" not in evidence:
        errors.append("evidence-router missing reusable knowledge discovery")
    catalog = (BASE / "skills/skill-catalog/SKILL.md").read_text(encoding="utf-8")
    if "Search broadly" not in catalog or "search-leverage" not in catalog:
        errors.append("skill-catalog missing search broadly / search-leverage discovery")
    script = (BASE / "scripts/skill-catalog.py").read_text(encoding="utf-8")
    if "search-leverage" not in script or "search-foundations" not in script:
        errors.append("skill-catalog.py missing foundation/leverage search commands")
    return errors


def check_project_fixture_layout() -> list[str]:
    errors: list[str] = []
    required = (
        PROJECT_FIXTURE / "src" / "components" / "Dashboard.tsx",
        PROJECT_FIXTURE / "reference" / "good-backend" / "README.md",
        PROJECT_FIXTURE / "reference" / "web" / "good-ui" / "REFERENCE.md",
        PROJECT_FIXTURE / "reference" / "web" / "good-ui" / "manifest.json",
    )
    for path in required:
        if not path.is_file():
            errors.append(f"project fixture missing {path.relative_to(BASE)}")
    return errors


def check_leverage_fixture_layout() -> list[str]:
    errors: list[str] = []
    required = (
        LEVERAGE_FIXTURE / "skills" / "dashboard-patterns" / "SKILL.md",
        LEVERAGE_FIXTURE / "skills" / "unrelated-noise-skill" / "SKILL.md",
        LEVERAGE_FIXTURE / "foundation-pack" / "dashboard-settings-foundation" / "SKILL.md",
        LEVERAGE_FIXTURE / "foundation-pack" / "unrelated-noise-foundation" / "SKILL.md",
    )
    for path in required:
        if not path.is_file():
            errors.append(f"leverage fixture missing {path.relative_to(BASE)}")
    return errors


def check_ranked_discovery() -> list[str]:
    errors: list[str] = []
    mod = _load_skill_catalog()
    skills = mod.scan(skills_dir=LEVERAGE_FIXTURE / "skills")
    foundations = mod.scan_foundations(pack_dir=LEVERAGE_FIXTURE / "foundation-pack")
    query = "dashboard settings page"
    skill_hits = mod.search(skills, query, 5)
    foundation_hits = mod.search_foundations(foundations, query, 5)
    if not skill_hits or skill_hits[0]["name"] != "dashboard-patterns":
        errors.append(f"fixture skill search expected dashboard-patterns first, got {skill_hits[:2]}")
    if skill_hits and any(h["name"] == "unrelated-noise-skill" for h in skill_hits[:1]):
        errors.append("fixture skill search ranked noise skill first")
    if not foundation_hits or foundation_hits[0]["name"] != "dashboard-settings-foundation":
        errors.append(
            f"fixture foundation search expected dashboard-settings-foundation first, got {foundation_hits[:2]}")
    if foundation_hits and any(h["name"] == "unrelated-noise-foundation" for h in foundation_hits[:1]):
        errors.append("fixture foundation search ranked noise foundation first")
    return errors


def check_cli_search_leverage() -> list[str]:
    errors: list[str] = []
    env = os.environ.copy()
    env["SKILLS_ROOT"] = str(LEVERAGE_FIXTURE / "skills")
    env["FOUNDATION_PACK"] = str(LEVERAGE_FIXTURE / "foundation-pack")
    proc = subprocess.run(
        [sys.executable, str(BASE / "scripts/skill-catalog.py"), "search-leverage",
         "dashboard settings", "--limit", "3"],
        capture_output=True, text=True, env=env, check=False,
    )
    if proc.returncode != 0:
        errors.append(f"search-leverage CLI failed: {proc.stderr.strip() or proc.stdout.strip()}")
        return errors
    out = proc.stdout
    if "dashboard-patterns" not in out:
        errors.append("search-leverage CLI missing dashboard-patterns")
    if "dashboard-settings-foundation" not in out:
        errors.append("search-leverage CLI missing dashboard-settings-foundation")
    if "unrelated-noise-skill" in out.split("dashboard-patterns")[0]:
        errors.append("search-leverage CLI ranked noise skill above relevant skill")
    return errors


def selftest() -> int:
    ok = True
    for label, fn in (
        ("project fixture layout", check_project_fixture_layout),
        ("leverage fixture layout", check_leverage_fixture_layout),
        ("policy triggers", check_policy_triggers),
        ("ranked discovery", check_ranked_discovery),
        ("CLI search-leverage", check_cli_search_leverage),
    ):
        errors = fn()
        if errors:
            ok = False
            print(f"FAIL {label}:")
            for e in errors:
                print(f"  {e}")
        else:
            print(f"PASS {label}")
    print("leverage-discovery-fixture selftest: PASS" if ok else "leverage-discovery-fixture selftest: FAIL")
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    errors = (
        check_project_fixture_layout()
        + check_leverage_fixture_layout()
        + check_policy_triggers()
        + check_ranked_discovery()
        + check_cli_search_leverage()
    )
    for e in errors:
        print(f"FAIL  {e}")
    print(f"LEVERAGE DISCOVERY FIXTURE: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
