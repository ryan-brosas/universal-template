#!/usr/bin/env python3
"""Print a read-only snapshot of installed host and model capabilities.

This optional diagnostic reports native command output. It does not rank models,
assign roles, infer authentication from installation, or choose a lane.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time

COMMANDS = (
    ("gh", ["gh", "--version"]),
    ("gh-auth", ["gh", "auth", "status"]),
    ("pi", ["pi", "--version"]),
    ("pi-models", ["pi", "--list-models"]),
    ("veda", ["veda", "--version"]),
    ("veda-models", ["veda", "models"]),
    ("veda-personas", ["veda", "personas"]),
    ("agy-models", ["agy", "models"]),
)


def run(command: list[str], timeout: int = 60) -> dict:
    executable = command[0]
    if shutil.which(executable) is None:
        return {"command": command, "status": "missing", "exit_code": None, "output": ""}
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "status": "error", "exit_code": None, "output": str(exc)}
    output = (result.stdout or result.stderr).strip()
    return {
        "command": command,
        "status": "ok" if result.returncode == 0 else "unavailable",
        "exit_code": result.returncode,
        "output": output,
    }


def collect() -> list[dict]:
    return [{"name": name, **run(command)} for name, command in COMMANDS]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    records = collect()
    if args.json:
        print(json.dumps({"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "probes": records}, indent=2))
    else:
        for record in records:
            first = record["output"].splitlines()[0][:120] if record["output"] else ""
            print(f"{record['status']:11} {record['name']:16} {first}")
        print("Diagnostic only: inspect native output and choose from task requirements.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
