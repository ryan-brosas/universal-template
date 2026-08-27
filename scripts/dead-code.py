#!/usr/bin/env python3
"""Dead-code check for the catalog — unused root scripts.

Adapted from pi-template dead-code.py (pack/manifest checks removed). A root
scripts/*.py must be referenced from a workflow, AGENTS.md, README, skill docs,
or another tracked script.

Exit 0 = no dead scripts. Non-zero = report.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
errors: list[str] = []
SKIP_DIRS = {".git", ".idea", ".pi", "node_modules", ".venv", "__pycache__", "scripts"}


def corpus_outside_scripts() -> str:
    parts: list[str] = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith((".yml", ".yaml", ".md", ".py", ".toml")):
                path = Path(root) / name
                try:
                    parts.append(path.read_text(encoding="utf-8"))
                except (UnicodeDecodeError, OSError):
                    pass
    # cross-references among scripts
    scripts = BASE / "scripts"
    if scripts.is_dir():
        for f in scripts.glob("*.py"):
            try:
                parts.append(f.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                pass
    return "\n".join(parts)


def main() -> int:
    text = corpus_outside_scripts()
    scripts = BASE / "scripts"
    if not scripts.is_dir():
        print("DEAD CODE OK (no scripts/)")
        return 0
    for f in sorted(scripts.glob("*.py")):
        own = f.read_text(encoding="utf-8")
        others = text.replace(own, "")
        if f.name not in others and f"scripts/{f.name}" not in others:
            errors.append(f"unused script (not referenced anywhere): scripts/{f.name}")
    if errors:
        print("DEAD CODE:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("DEAD CODE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
