#!/usr/bin/env python3
"""Preview or atomically apply a scoped MCP selection to one JSON host config."""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REGISTRY = BASE / "mcp/servers.json"
PROFILES = BASE / "mcp/profiles.json"
PLACEHOLDER = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def selection(profile: str | None, server: str | None) -> tuple[list[str], dict]:
    registry = load_json(REGISTRY).get("mcpServers", {})
    profiles = load_json(PROFILES).get("profiles", {})
    names = [server] if server else profiles.get(profile)
    if names is None:
        raise ValueError(f"unknown MCP profile: {profile}")
    missing = sorted(set(names) - set(registry))
    if missing:
        raise ValueError("profile references unknown servers: " + ", ".join(missing))
    return list(names), registry


def translate(config: dict, format_name: str) -> dict:
    out = {key: copy.deepcopy(value) for key, value in config.items() if key != "lifecycle"}
    if format_name != "prime":
        return out
    if out.get("type", "stdio") == "remote":
        out["type"] = "http"
    env = out.get("env")
    if isinstance(env, dict):
        translated = {}
        for key, value in env.items():
            match = PLACEHOLDER.fullmatch(str(value))
            if not match:
                raise ValueError(f"Prime requires an env placeholder for {key}, not a literal")
            translated[key] = {"env": match.group(1)}
        out["env"] = translated
    return out


def reconcile(
    current: dict, names: list[str], registry: dict, deactivate: bool, format_name: str
) -> dict:
    result = copy.deepcopy(current)
    servers = result.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("target mcpServers must be an object")
    if deactivate:
        for name in names:
            servers.pop(name, None)
    else:
        for name in names:
            servers[name] = translate(registry[name], format_name)
    return result


def atomic_write(path: Path, value: dict, replace=os.replace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def selftest() -> int:
    with tempfile.TemporaryDirectory(prefix="mcp-configure-") as raw:
        path = Path(raw) / "settings.json"
        path.write_text('{"theme":"dark","mcpServers":{"owned":{"command":"keep"}}}\n', encoding="utf-8")
        names, registry = selection("docs", None)
        updated = reconcile(load_json(path), names, registry, False, "generic")
        atomic_write(path, updated)
        assert updated["theme"] == "dark" and "owned" in updated["mcpServers"]
        assert set(updated["mcpServers"]) == {"owned", "context7"}
        removed = reconcile(updated, names, registry, True, "generic")
        atomic_write(path, removed)
        assert removed["mcpServers"] == {"owned": {"command": "keep"}}
        before = path.read_text(encoding="utf-8")

        def fail_replace(_source, _target):
            raise OSError("injected replace failure")
        try:
            atomic_write(path, {"changed": True}, replace=fail_replace)
        except OSError:
            pass
        assert path.read_text(encoding="utf-8") == before
        assert not list(path.parent.glob(f".{path.name}.*"))
        empty, _ = selection("minimal", None)
        assert empty == []
    print("MCP CONFIGURE SELFTEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--profile")
    group.add_argument("--server")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--format", choices=("generic", "prime"), default="generic")
    parser.add_argument("--deactivate", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.target or (not args.profile and not args.server):
        parser.error("--target and exactly one of --profile/--server are required")
    names, registry = selection(args.profile, args.server)
    current = load_json(args.target.expanduser())
    updated = reconcile(current, names, registry, args.deactivate, args.format)
    print(json.dumps(updated, indent=2))
    if args.apply:
        atomic_write(args.target.expanduser(), updated)
        print(f"WROTE {args.target.expanduser()}")
    else:
        print("[preview only] pass --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
