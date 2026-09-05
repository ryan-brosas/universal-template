#!/usr/bin/env python3
"""Preview or safely reconcile a scoped MCP selection in one JSON host config."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REGISTRY = BASE / "mcp/servers.json"
PROFILES = BASE / "mcp/profiles.json"
PLACEHOLDER = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")


def read_bytes(path: Path) -> bytes | None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"expected a regular file, not a symlink or directory: {path}")
    return path.read_bytes() if path.exists() else None


def decode_json(raw: bytes | None, path: Path) -> dict:
    value = {} if raw is None else json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_json(path: Path) -> dict:
    return decode_json(read_bytes(path), path)


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


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def digest(raw: bytes | None) -> str | None:
    return None if raw is None else hashlib.sha256(raw).hexdigest()


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".universal-template-mcp.json")


def backup_path(path: Path) -> Path:
    return path.with_name(path.name + ".before-universal-template-mcp")


def lock_path(path: Path) -> Path:
    return path.with_name(path.name + ".universal-template-mcp.lock")


def state_document(path: Path, managed: dict) -> dict:
    return {"version": 1, "target": str(path), "managed": managed}


def validate_managed(value: object) -> dict:
    if not isinstance(value, dict) or any(
        not isinstance(name, str) or not isinstance(sha, str) or not DIGEST.fullmatch(sha)
        for name, sha in value.items()
    ):
        raise ValueError("invalid managed-entry fingerprints")
    return value


def ownership(path: Path, raw: bytes | None, target_raw: bytes | None) -> dict:
    if raw is None:
        return {}
    state = decode_json(raw, sidecar(path))
    if (type(state.get("version")) is not int or state["version"] != 1
            or state.get("target") != str(path)
            or set(state) - {"version", "target", "managed", "pending"}):
        raise ValueError("invalid or foreign MCP ownership sidecar")
    managed = validate_managed(state.get("managed"))
    if "pending" not in state:
        return managed
    pending = state["pending"]
    if not isinstance(pending, dict) or set(pending) != {"before", "after", "managed"}:
        raise ValueError("invalid pending MCP transaction")
    for key in ("before", "after"):
        sha = pending[key]
        if not (key == "before" and sha is None) and (
            not isinstance(sha, str) or not DIGEST.fullmatch(sha)
        ):
            raise ValueError("invalid pending MCP transaction digest")
    next_managed = validate_managed(pending["managed"])
    current = digest(target_raw)
    if current == pending["after"]:
        return next_managed
    if current == pending["before"]:
        return managed
    raise ValueError("interrupted MCP transaction and target changed; inspect target, sidecar, and backup before retrying")


def reconcile(current: dict, names: list[str], registry: dict, deactivate: bool,
              format_name: str, managed: dict, *, profile: bool,
              replace_unmanaged: bool = False) -> tuple[dict, dict, dict]:
    result = copy.deepcopy(current)
    servers = result.get("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("target mcpServers must be an object")
    owned = {name: sha for name, sha in managed.items()
             if name in servers and fingerprint(servers[name]) == sha}
    modified = sorted(name for name in managed if name in servers and name not in owned)
    next_managed = dict(owned)
    changes = {"add": [], "replace": [], "remove": [], "preserve_modified": modified}
    # Profiles replace the managed set. Single-server activation is additive.
    remove = (set(owned) if not names else set(names)) if deactivate else (
        set(owned) - set(names) if profile else set()
    )
    for name in sorted(remove & set(owned)):
        del servers[name]
        next_managed.pop(name, None)
        changes["remove"].append(name)
    if not deactivate:
        for name in names:
            config = translate(registry[name], format_name)
            if name in servers and name not in owned and not replace_unmanaged:
                raise ValueError(f"unmanaged MCP entry conflicts: {name}; inspect it or explicitly use --replace-unmanaged")
            if name not in servers:
                changes["add"].append(name)
            elif servers[name] != config or name not in owned:
                changes["replace"].append(name)
            servers[name] = config
            next_managed[name] = fingerprint(config)
            if name in changes["preserve_modified"]:
                changes["preserve_modified"].remove(name)
    if servers or "mcpServers" in current:
        result["mcpServers"] = servers
    return result, next_managed, changes


def sync_directory(path: Path) -> None:
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def access_metadata(path: Path) -> tuple:
    # Python exposes Linux ACLs through xattrs, but not macOS/Windows ACLs.
    # Refuse existing-file replacement where we cannot prove preservation.
    if not sys.platform.startswith("linux") or not hasattr(os, "listxattr"):
        raise ValueError("existing config replacement requires Linux access-metadata support; use host-native tooling on this platform")
    info = path.stat()
    attrs = {name: os.getxattr(path, name, follow_symlinks=False)
             for name in os.listxattr(path, follow_symlinks=False)}
    return info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode), attrs


def set_access_metadata(path: Path, access: tuple) -> None:
    uid, gid, mode, attrs = access
    info = path.stat()
    if (info.st_uid, info.st_gid) != (uid, gid):
        os.chown(path, uid, gid)
    for name in set(os.listxattr(path)) - set(attrs):
        os.removexattr(path, name)
    os.chmod(path, mode)
    for name, value in attrs.items():
        if name not in os.listxattr(path) or os.getxattr(path, name) != value:
            os.setxattr(path, name, value)
    if access_metadata(path) != access:
        raise OSError("cannot preserve existing config access metadata")


def atomic_write(path: Path, raw: bytes, *, mode: int = 0o600,
                 access: tuple | None = None, replace=os.replace) -> None:
    read_bytes(path)  # Refuse symlink targets, including dangling ones.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            if access is None:
                os.chmod(temp, mode)
            else:
                set_access_metadata(temp, access)
            os.fsync(stream.fileno())
        replace(temp, path)
        sync_directory(path.parent)
        if read_bytes(path) != raw:
            raise OSError(f"read-back validation failed: {path}")
        if access is not None and access_metadata(path) != access:
            raise OSError(f"access metadata read-back validation failed: {path}")
    finally:
        temp.unlink(missing_ok=True)


def first_backup(path: Path, raw: bytes) -> None:
    backup = backup_path(path)
    if read_bytes(backup) is not None:
        return
    fd, name = tempfile.mkstemp(prefix=f".{backup.name}.", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Link publishes a complete backup without ever replacing an existing one.
        os.link(temp, backup)
        sync_directory(path.parent)
        if read_bytes(backup) != raw:
            raise OSError("backup read-back validation failed")
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path(path)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError(f"MCP configuration is locked: {lock}; inspect the owning process before removing an abandoned lock") from None
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()) + "\n")
        yield
    finally:
        lock.unlink()


def apply_plan(path: Path, before: bytes | None, state_before: bytes | None,
               current: dict, updated: dict, managed: dict, next_managed: dict) -> None:
    state_path = sidecar(path)
    after = before if updated == current else encoded(updated)
    final = encoded(state_document(path, next_managed))
    if read_bytes(path) != before or read_bytes(state_path) != state_before:
        raise ValueError("MCP target or ownership changed during planning; retry")
    if after != before:
        access = access_metadata(path) if before is not None else None
        if before is not None:
            first_backup(path, before)
        journal = state_document(path, managed)
        journal["pending"] = {"before": digest(before), "after": digest(after), "managed": next_managed}
        atomic_write(state_path, encoded(journal))
        if read_bytes(path) != before:
            raise ValueError("MCP target changed before replacement; inspect the pending transaction")
        atomic_write(path, after, access=access)
    # Empty unmanaged selections are no-ops; existing journals are finalized.
    if state_before is not None or next_managed or after != before:
        if read_bytes(state_path) != final:
            atomic_write(state_path, final)


def configure_target(path: Path, names: list[str], registry: dict, *, profile: bool,
                     deactivate: bool = False, format_name: str = "generic",
                     replace_unmanaged: bool = False, apply: bool = False) -> dict:
    before = read_bytes(path)
    state_before = read_bytes(sidecar(path))
    current = decode_json(before, path)
    managed = ownership(path, state_before, before)
    updated, next_managed, changes = reconcile(
        current, names, registry, deactivate, format_name, managed,
        profile=profile, replace_unmanaged=replace_unmanaged,
    )
    final_state = encoded(state_document(path, next_managed))
    would_write = updated != current or (
        (state_before is not None or bool(next_managed)) and state_before != final_state
    )
    if apply:
        apply_plan(path, before, state_before, current, updated, managed, next_managed)
    # Never dump config values: unmanaged entries may contain literal credentials.
    return {"target": str(path), **changes, "would_write": would_write, "applied": apply}


def selftest() -> int:
    suite = unittest.defaultTestLoader.discover(str(BASE / "mcp"), pattern="test_configure.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        return 1
    print("MCP CONFIGURE SELFTEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--profile", help="replace the managed set with this profile")
    group.add_argument("--server", help="add/update one managed server")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--format", choices=("generic", "prime"), default="generic")
    parser.add_argument("--deactivate", action="store_true", help="remove only selected entries still owned by this tool")
    parser.add_argument("--replace-unmanaged", action="store_true", help="explicitly replace and adopt selected unmanaged entries")
    parser.add_argument("--apply", action="store_true", help="write changes; otherwise preview without modifying files")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.target or (not args.profile and not args.server):
        parser.error("--target and exactly one of --profile/--server are required")
    if args.deactivate and args.replace_unmanaged:
        parser.error("--replace-unmanaged cannot be combined with --deactivate")
    # Resolve the parent, but not the final component: final symlinks must fail.
    expanded = args.target.expanduser().absolute()
    path = expanded.parent.resolve() / expanded.name
    try:
        names, registry = selection(args.profile, args.server)
        options = dict(profile=args.profile is not None, deactivate=args.deactivate,
                       format_name=args.format, replace_unmanaged=args.replace_unmanaged,
                       apply=False)
        summary = configure_target(path, names, registry, **options)
        if args.apply and summary["would_write"]:
            # Replan under the lock; the unlocked preview is not mutation authority.
            options["apply"] = True
            with locked(path):
                summary = configure_target(path, names, registry, **options)
        elif args.apply:
            summary["applied"] = True
        print(json.dumps(summary, indent=2))
        if not args.apply:
            print("[preview only] pass --apply to write")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"MCP configuration failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
