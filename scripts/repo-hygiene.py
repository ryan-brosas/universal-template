#!/usr/bin/env python3
"""Check exact repository publication contracts.

The gate owns bytes and structure: required files, whitespace, structured-data
parsing, obvious credential patterns, portable MCP paths, and file-size limits.
It does not judge prose or policy meaning.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024
TEXT_EXT = {".md", ".json", ".yml", ".yaml", ".py", ".mjs", ".ts", ".toml", ".txt", ".sh"}
SKIP_DIRS = {".git", ".idea", ".pi", "node_modules", ".venv", "__pycache__"}
REQUIRED = (
    "AGENTS.md", "README.md", "CONTRIBUTING.md", "SECURITY.md",
    "prompts", "skills", "templates", "mcp/servers.json",
    "templates/agents.md", "templates/project-context.md", "templates/roadmap.md",
    "templates/readme.md", "templates/pull-request.md", "templates/github-pr-ci.yml",
    "templates/skill.md",
)
LARGE_EXEMPT_SUFFIXES = ("/sdk/browser_protocol.json", "/sdk/js_protocol.json")
SECRET_PATTERNS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI-style key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "GitHub token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"(?i)(api[_-]?key|client[_-]?secret|password|auth[_-]?token)\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"), "possible secret"),
)


def is_vendored(rel: str) -> bool:
    return "/sdk/" in f"/{rel}/" or "/learnings/" in f"/{rel}/"


def files() -> list[Path]:
    found: list[Path] = []
    for root, dirs, names in os.walk(BASE):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not name.endswith(".bak")]
        for name in names:
            if not name.endswith((".bak", ".jsonl", ".swp", ".tmp", ".log")):
                found.append(Path(root) / name)
    return found


def parse_structured(path: Path, text: str, errors: list[str]) -> None:
    rel = path.relative_to(BASE)
    try:
        if path.suffix == ".json":
            json.loads(text)
        elif path.suffix == ".toml":
            import tomllib
            tomllib.loads(text)
        elif path.suffix in {".yml", ".yaml"}:
            try:
                import yaml
            except ImportError:
                errors.append("PyYAML is required for maintainer validation of YAML files")
                return
            yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"invalid {path.suffix.lstrip('.').upper()}: {rel}: {exc}")


def check_mcp(errors: list[str]) -> None:
    path = BASE / "mcp/servers.json"
    try:
        servers = json.loads(path.read_text(encoding="utf-8"))["mcpServers"]
    except Exception as exc:  # noqa: BLE001
        errors.append(f"mcp/servers.json missing mcpServers object: {exc}")
        return
    if not isinstance(servers, dict):
        errors.append("mcp/servers.json mcpServers must be an object")
        return
    machine_paths = ("/home/", "/mnt/", "/Users/", "C:\\")
    for name, config in servers.items():
        if not isinstance(config, dict):
            errors.append(f"mcp/servers.json: {name} config must be an object")
            continue
        values = [config.get("command", ""), *(config.get("args") or [])]
        values.extend((config.get("env") or {}).values())
        for value in values:
            if isinstance(value, str) and (value.startswith("/") or any(part in value for part in machine_paths)):
                errors.append(f"mcp/servers.json: {name} contains machine-local path: {value}")


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (BASE / relative).exists():
            errors.append(f"required path missing: {relative}")
    if (BASE / ".gitmodules").exists():
        errors.append("git submodules are forbidden (.gitmodules present)")
    for path in files():
        rel = str(path.relative_to(BASE))
        if is_vendored(rel):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_BYTES and not any(rel.endswith(suffix) for suffix in LARGE_EXEMPT_SUFFIXES):
            errors.append(f"large file ({size // 1024}KB > 1024KB): {rel}")
        if path.suffix.lower() not in TEXT_EXT:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "\r\n" in text and "\n" in text.replace("\r\n", ""):
            errors.append(f"mixed line endings: {rel}")
        if any(line != line.rstrip(" \t") for line in text.splitlines()):
            errors.append(f"trailing whitespace: {rel}")
        if text and not text.endswith("\n"):
            errors.append(f"missing EOF newline: {rel}")
        parse_structured(path, text, errors)
        if path.suffix.lower() != ".md":
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"{label} in {rel}")
                    break
    check_mcp(errors)
    for error in errors[:100]:
        print(f"FAIL  {error}")
    if len(errors) > 100:
        print(f"FAIL  ... {len(errors) - 100} more")
    print(f"REPOSITORY CONTRACTS: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
