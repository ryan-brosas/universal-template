#!/usr/bin/env python3
"""Catalog integrity — structural consistency without pack routers.

Replaces pi-template check-integrity for the flat ~/.agents/skills layout:
- mcp/servers.json is valid JSON with expected server keys
- every skill directory contains SKILL.md
- AGENTS.md documents the catalog gate command

Exit 0 = consistent. Non-zero = drift.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
errors: list[str] = []

EXPECTED_MCP = {"codebase-memory", "context7", "deepwiki", "exa", "openviking"}


def check_mcp() -> None:
    path = BASE / "mcp" / "servers.json"
    if not path.is_file():
        errors.append("missing mcp/servers.json")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"mcp/servers.json invalid JSON: {exc}")
        return
    servers = data.get("mcpServers", data) if isinstance(data, dict) else {}
    if not isinstance(servers, dict):
        errors.append("mcp/servers.json: expected object of servers")
        return
    missing = EXPECTED_MCP - set(servers.keys())
    if missing:
        errors.append(f"mcp/servers.json missing servers: {sorted(missing)}")


def check_skills_present() -> None:
    skills = BASE / "skills"
    if not skills.is_dir():
        errors.append("skills/ missing")
        return
    for entry in sorted(skills.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            if not (entry / "SKILL.md").is_file():
                errors.append(f"skill missing SKILL.md: {entry.name}")


def check_agents_gate() -> None:
    agents = BASE / "AGENTS.md"
    if not agents.is_file():
        errors.append("missing AGENTS.md")
        return
    text = agents.read_text(encoding="utf-8")
    for needle in (
        "skill-validator.py",
        "repo-hygiene.py",
        "catalog-quality.py",
    ):
        if needle not in text:
            errors.append(f"AGENTS.md must document {needle} in the catalog gate")


def check_readme() -> None:
    """README claims match disk: template count, inventory pointer, no retired names."""
    readme = BASE / "README.md"
    if not readme.is_file():
        errors.append("missing README.md")
        return
    text = readme.read_text(encoding="utf-8")
    on_disk = [p for p in (BASE / "templates").iterdir()
               if p.is_file() and p.name != "source.yml"]
    m = re.search(r"(\d+)\s+CLI-neutral format templates", text)
    if m and int(m.group(1)) != len(on_disk):
        errors.append(
            f"README claims {m.group(1)} format templates; disk has {len(on_disk)} "
            f"(excluding source.yml) - see references/templates-inventory.md")
    if "references/templates-inventory.md" not in text:
        errors.append("README must point at references/templates-inventory.md as the canonical template inventory")
    for retired in ("project.md", "state.md", "tech-stack.md", "user.md"):
        if retired in text:
            errors.append(f"README lists retired template as current: {retired}")
    if re.search(r"one-page principles", text):
        errors.append("README hard-codes an essentials count; point at essentials/README.md instead")


def check_generated_catalogs() -> None:
    """docs/skill-catalog.md and docs/foundation-catalog.md must be current."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "skill_catalog", str(Path(__file__).with_name("skill-catalog.py")))
    if spec is None or spec.loader is None:
        errors.append("cannot load scripts/skill-catalog.py")
        return
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        targets = mod.build_docs(mod.scan())
    except Exception as exc:  # noqa: BLE001 - missing/broken generator is a normal failure
        errors.append(
            f"cannot load scripts/skill-catalog.py ({type(exc).__name__}: {exc}); "
            f"the generated-catalog check cannot run - restore the script and rerun")
        return
    for rel, content in targets.items():
        p = BASE / rel
        if not p.is_file() or p.read_text(encoding="utf-8") != content:
            errors.append(
                f"generated catalog stale: {rel} "
                f"(rerun python3 scripts/skill-catalog.py generate)")


def main() -> int:
    check_mcp()
    check_skills_present()
    check_agents_gate()
    check_readme()
    check_generated_catalogs()
    if errors:
        print("CATALOG INTEGRITY FAILURES:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("CATALOG INTEGRITY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
