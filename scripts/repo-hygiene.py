#!/usr/bin/env python3
"""Repo-hygiene check — mechanical anti-slop for the global skill catalog.

Ported from the absorbed pi-template gate (practices-to-ci / essentials Pillar 4).
Enforces:
- no trailing whitespace
- files end with a newline
- no smart quotes / ligatures in code/config (not prose .md)
- no large authored files (default >1MB; vendored protocol dumps exempt)
- YAML / JSON / TOML validity
- lightweight typo scan on top-level docs + practice SKILL.md files
- lightweight secret-pattern scan
- no .gitmodules

Exit 0 = clean. Non-zero = report what to fix.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MAX_KB = 1024
errors: list[str] = []

TEXT_EXT = {".md", ".json", ".yml", ".yaml", ".py", ".mjs", ".ts", ".toml", ".txt", ".sh"}
CODE_EXT = {".py", ".mjs", ".ts", ".json", ".yml", ".yaml", ".toml", ".env"}
SKIP_DIRS = {".git", ".idea", ".pi", "node_modules", ".venv", "__pycache__"}

# Vendored / generated / example dumps (size + formatting exempt)
LARGE_EXEMPT_SUFFIXES = (
    "/sdk/browser_protocol.json",
    "/sdk/js_protocol.json",
)

def is_vendored_path(rel: str) -> bool:
    return (
        "/sdk/" in f"/{rel}/"
        or "/learnings/" in f"/{rel}/"
        or rel.endswith("/sdk/browser_protocol.json")
        or rel.endswith("/sdk/js_protocol.json")
    )

TYPO_MAP = {
    "recieve": "receive",
    "seperate": "separate",
    "occured": "occurred",
    "adress": "address",
    "definately": "definitely",
    "untill": "until",
    "compatability": "compatibility",
    "dependancy": "dependency",
    "enviroment": "environment",
    "existance": "existence",
    "fucntion": "function",
    "paramter": "parameter",
    "retrun": "return",
    "wether": "whether",
}


def walk() -> list[Path]:
    out: list[Path] = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith(".bak")]
        for name in files:
            if name.endswith((".bak", ".jsonl", ".swp", ".tmp", ".log")):
                continue
            out.append(Path(root) / name)
    return out


def is_large_exempt(rel: str) -> bool:
    return any(rel.endswith(sfx) or sfx in rel for sfx in LARGE_EXEMPT_SUFFIXES)


def check_file(path: Path) -> None:
    rel = str(path.relative_to(BASE))
    ext = path.suffix.lower()

    if is_vendored_path(rel):
        return

    try:
        size_kb = path.stat().st_size / 1024
        if size_kb > MAX_KB and not is_large_exempt(rel):
            errors.append(f"large file ({size_kb:.0f}KB > {MAX_KB}KB): {rel}")
    except OSError:
        return

    if ext not in TEXT_EXT:
        return

    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return

    if "\r\n" in content and "\n" in content.replace("\r\n", ""):
        errors.append(f"mixed line endings: {rel}")

    for i, line in enumerate(content.splitlines(), 1):
        if line != line.rstrip(" \t"):
            errors.append(f"trailing whitespace: {rel}:{i}")
            break

    if content and not content.endswith("\n"):
        errors.append(f"missing EOF newline: {rel}")

    # Smart quotes in code/config only — prose markdown may keep typography.
    if ext in CODE_EXT:
        for ch, name in (
            ("\u201c", "smart quote"),
            ("\u201d", "smart quote"),
            ("\u2018", "smart quote"),
            ("\u2019", "smart quote"),
            ("\ufb01", "ligature fi"),
            ("\ufb02", "ligature fl"),
        ):
            if ch in content:
                errors.append(f"{name} in {rel}")
                break

    if ext == ".json":
        try:
            json.loads(content)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid JSON: {rel}: {exc}")

    if ext == ".toml":
        try:
            import tomllib

            tomllib.loads(content)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid TOML: {rel}: {exc}")

    if ext in CODE_EXT:
        secret_patterns = [
            (r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "possible secret"),
            (r"sk-[A-Za-z0-9]{20,}", "OpenAI-style key"),
            (r"ghp_[A-Za-z0-9]{20,}", "GitHub token"),
            (r"AKIA[0-9A-Z]{16}", "AWS access key"),
        ]
        for pat, label in secret_patterns:
            if re.search(pat, content):
                errors.append(f"{label} in {rel}")
                break

    # Typos: top-level docs + practice SKILL.md only.
    typo_target = False
    if rel in {"AGENTS.md", "README.md"} or rel.startswith("essentials/"):
        typo_target = True
    if rel.startswith("skills/") and rel.endswith("/SKILL.md"):
        typo_target = True
    if typo_target and ext == ".md":
        for word, fix in TYPO_MAP.items():
            if re.search(rf"\b{word}\b", content, re.IGNORECASE):
                errors.append(f"typo '{word}' (should be '{fix}'): {rel}")
                break


def check_yaml() -> None:
    try:
        import yaml
    except ImportError:
        return
    for path in list((BASE / ".github" / "workflows").glob("*.yml")) + list((BASE / "templates").glob("*.yml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid YAML: {path.relative_to(BASE)}: {exc}")


def main() -> int:
    if (BASE / ".gitmodules").exists():
        errors.append("git submodules are forbidden (.gitmodules present)")

    for path in walk():
        check_file(path)
    check_yaml()

    if errors:
        print("REPO HYGIENE FAILURES:")
        for err in errors[:80]:
            print(f"  - {err}")
        if len(errors) > 80:
            print(f"  ... {len(errors)} total")
        else:
            print(f"  ... {len(errors)} total")
        return 1
    print("REPO HYGIENE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
