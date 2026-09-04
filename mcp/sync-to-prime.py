#!/usr/bin/env python3
"""Compatibility wrapper for scoped Prime MCP activation.

Preview-only by default. Selection is mandatory; no command enables the whole
registry implicitly. Prefer mcp/configure.py for new automation.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TARGET = Path.home() / ".prime/agent/settings.json"


def main() -> int:
    args = sys.argv[1:]
    if not any(arg == "--server" or arg == "--profile" for arg in args):
        print("select exactly one --server NAME or --profile NAME", file=sys.stderr)
        return 2
    command = [
        sys.executable,
        str(BASE / "mcp/configure.py"),
        "--format", "prime",
        "--target", str(TARGET),
        *args,
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
