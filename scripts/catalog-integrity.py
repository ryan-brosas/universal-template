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


def main() -> int:
    check_mcp()
    check_skills_present()
    check_agents_gate()
    if errors:
        print("CATALOG INTEGRITY FAILURES:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("CATALOG INTEGRITY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
