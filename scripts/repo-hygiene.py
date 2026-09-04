#!/usr/bin/env python3
"""Check tracked publication bytes, structure, secrets, paths, and ownership."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024
TEXT_EXT = {".md", ".json", ".yml", ".yaml", ".py", ".mjs", ".ts", ".toml", ".txt", ".sh"}
REQUIRED = (
    "AGENTS.md", "README.md", "CONTRIBUTING.md", "SECURITY.md", "prompts", "skills",
    "templates", "mcp/servers.json", "mcp/profiles.json", "mcp/configure.py",
    "templates/agents.md", "templates/project-context.md", "templates/roadmap.md",
    "templates/readme.md", "templates/pull-request.md", "templates/github-pr-ci.yml",
    "templates/skill.md",
)
LARGE_EXEMPT_SUFFIXES = ("/sdk/browser_protocol.json", "/sdk/js_protocol.json")
BANNED_ARTIFACT_SUFFIXES = (".jsonl", ".log", ".swp", ".tmp", ".bak")
SECRET_PATTERNS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI-style key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "GitHub token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"(?i)(api[_-]?key|client[_-]?secret|password|auth[_-]?token)\s*[:=]\s*['\"](?![A-Z][A-Z0-9_]*['\"])[^'\"\s$<{]{16,}['\"]"), "possible secret"),
)
# Split literals keep this gate from diagnosing its own source.
PRIVATE_PATTERNS = (
    re.compile("/Users/" + "monotykamary"),
    re.compile("/home/" + "utopia"),
    re.compile("/mnt/(?:hdd|ssd)/" + "utopia"),
    re.compile(r"\bAPPSYS\b|\bMAC-[0-9A-Fa-f]{12}\b"),
)


def tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(BASE), "ls-files", "-z"], capture_output=True, check=True
    )
    return [BASE / raw.decode("utf-8", "surrogateescape") for raw in result.stdout.split(b"\0") if raw]


def is_vendored(rel: str) -> bool:
    return "/sdk/" in f"/{rel}/" or "/learnings/" in f"/{rel}/"


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


def content_errors(rel: str, text: str) -> list[str]:
    errors: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"{label} in {rel}")
            break
    for pattern in PRIVATE_PATTERNS:
        if pattern.search(text):
            errors.append(f"private machine path or identifier in {rel}")
            break
    return errors


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
    for name, config in servers.items():
        if not isinstance(config, dict):
            errors.append(f"mcp/servers.json: {name} config must be an object")
            continue
        values = [config.get("command", ""), *(config.get("args") or [])]
        values.extend((config.get("env") or {}).values())
        for value in values:
            if isinstance(value, str) and value.startswith(("/home/", "/mnt/", "/Users/", "C:\\")):
                errors.append(f"mcp/servers.json: {name} contains machine-local path: {value}")


def path_contract_errors(rels: set[str]) -> list[str]:
    errors = [
        f"runtime/session artifact must not be tracked: {rel}"
        for rel in sorted(rels) if rel.endswith(BANNED_ARTIFACT_SUFFIXES)
    ]
    system = sorted(rel for rel in rels if rel.startswith("skills/.system/"))
    if system:
        errors.append(f"vendor runtime files must not be tracked: skills/.system/ ({len(system)} files)")
    return errors


def check(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    rels = {str(path.relative_to(BASE)) for path in paths}
    errors.extend(path_contract_errors(rels))
    for relative in REQUIRED:
        if not (BASE / relative).exists():
            errors.append(f"required path missing: {relative}")
    if ".gitmodules" in rels:
        errors.append("git submodules are forbidden (.gitmodules tracked)")
    for rel in sorted(rels):
        path = BASE / rel
        if not path.is_file():
            continue
        text: str | None = None
        if path.suffix.lower() in TEXT_EXT:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                pass
        # Credential and public-path checks cover every decodable tracked text
        # file, including vendored SDK/reference content.
        if text is not None:
            errors.extend(content_errors(rel, text))
        if is_vendored(rel):
            continue
        size = path.stat().st_size
        if size > MAX_BYTES and not any(rel.endswith(suffix) for suffix in LARGE_EXEMPT_SUFFIXES):
            errors.append(f"large file ({size // 1024}KB > 1024KB): {rel}")
        if text is None:
            continue
        if "\r\n" in text and "\n" in text.replace("\r\n", ""):
            errors.append(f"mixed line endings: {rel}")
        if any(line != line.rstrip(" \t") for line in text.splitlines()):
            errors.append(f"trailing whitespace: {rel}")
        if text and not text.endswith("\n"):
            errors.append(f"missing EOF newline: {rel}")
        parse_structured(path, text, errors)
    check_mcp(errors)
    return errors


def selftest() -> int:
    cases = (
        ("docs/x.md", "token = 'sk-" + "abcdefghijklmnopqrstuvwxyz'", "OpenAI-style key"),
        ("skills/demo/SKILL.md", "/home/" + "utopia/work/repo", "private machine path"),
        (
            "skills/demo-foundation/references/index.md",
            "/mnt/hdd/" + "utopia/evidence",
            "private machine path",
        ),
    )
    path_failures = path_contract_errors({"sessions/run.jsonl", "skills/.system/tool/SKILL.md"})
    artifacts_caught = any("runtime/session artifact" in item for item in path_failures)
    vendor_caught = any("vendor runtime" in item for item in path_failures)
    if not artifacts_caught or not vendor_caught:
        print(f"selftest failed for tracked-path exclusions: {path_failures}", file=sys.stderr)
        return 1
    for rel, text, expected in cases:
        found = content_errors(rel, text)
        if (expected is None and found) or (expected and not any(expected in item for item in found)):
            print(f"selftest failed for {rel}: {found}", file=sys.stderr)
            return 1
    print("REPOSITORY HYGIENE SELFTEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    errors = check(tracked_paths())
    for error in errors[:100]:
        print(f"FAIL  {error}")
    if len(errors) > 100:
        print(f"FAIL  ... {len(errors) - 100} more")
    print(f"REPOSITORY CONTRACTS: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
