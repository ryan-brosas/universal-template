#!/usr/bin/env python3
"""Check tracked publication bytes, structure, secrets, paths, and ownership."""
from __future__ import annotations

import argparse
import codecs
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from publication_fixtures import fixture_environment, fixture_git, require

BASE = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024
MAX_SCAN_BYTES = MAX_BYTES
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
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
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


def decodable_head(raw: bytes, *, truncated: bool = False) -> str | None:
    """Decode a bounded head for content scanning, or None for binary data.

    Strict decoding rejects unsupported bytes; only an actual bounded read may
    leave an incomplete trailing UTF-8 character.
    """
    if b"\0" in raw:
        return None
    try:
        return codecs.getincrementaldecoder("utf-8")().decode(raw, final=not truncated)
    except UnicodeDecodeError:
        return None


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
        errors.append(f"invalid {path.suffix.lstrip('.').upper()}: {rel} ({type(exc).__name__})")


def content_errors(rel: str, text: str) -> list[str]:
    errors: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"{label} in {rel}")
            break
    if PRIVATE_KEY_PATTERN.search(text):
        errors.append(f"private key material in {rel}")
    for pattern in PRIVATE_PATTERNS:
        if pattern.search(text):
            errors.append(f"private machine path or identifier in {rel}")
            break
    return errors


def large_file_error(rel: str, size: int) -> str | None:
    if size > MAX_BYTES and not any(rel.endswith(suffix) for suffix in LARGE_EXEMPT_SUFFIXES):
        return f"large file ({size // 1024}KB > 1024KB): {rel}"
    return None


def line_ending_errors(rel: str, text: str) -> list[str]:
    errors: list[str] = []
    if "\r\n" in text and "\n" in text.replace("\r\n", ""):
        errors.append(f"mixed line endings: {rel}")
    return errors


def check_mcp(errors: list[str]) -> None:
    path = BASE / "mcp/servers.json"
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            errors.append("mcp/servers.json too large for structured validation")
            return
        servers = json.loads(raw)["mcpServers"]
    except Exception as exc:  # noqa: BLE001
        errors.append(f"mcp/servers.json missing mcpServers object ({type(exc).__name__})")
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
                errors.append(f"mcp/servers.json: {name} contains machine-local path")


def path_contract_errors(rels: set[str]) -> list[str]:
    errors = [
        f"runtime/session artifact must not be tracked: {rel}"
        for rel in sorted(rels) if rel.endswith(BANNED_ARTIFACT_SUFFIXES)
    ]
    dot_runtime = sorted(
        rel for rel in rels
        if rel.startswith("skills/") and len(rel.split("/")) > 2 and rel.split("/")[1].startswith(".")
    )
    if dot_runtime:
        listed = ", ".join(dot_runtime[:5]) + (", ..." if len(dot_runtime) > 5 else "")
        errors.append(
            f"vendor runtime files must not be tracked under skills/: {listed} ({len(dot_runtime)} files)"
        )
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
        try:
            if path.is_symlink() or not path.is_file():
                errors.append(f"tracked input is missing or not a regular file: {rel}")
                continue
            size = path.stat().st_size
            large = large_file_error(rel, size)
            if large:
                errors.append(large)
            with path.open("rb") as stream:
                raw = stream.read(MAX_SCAN_BYTES + 1)
        except OSError:
            errors.append(f"unreadable tracked file: {rel}")
            continue
        truncated = len(raw) > MAX_SCAN_BYTES
        raw = raw[:MAX_SCAN_BYTES]
        head = decodable_head(raw, truncated=truncated)
        if head is None:
            print(f"SKIP text safety scan (binary or unsupported UTF-8): {rel}", file=sys.stderr)
            if path.suffix.lower() in TEXT_EXT and b"\0" not in raw:
                errors.append(f"unsupported text encoding: {rel}")
        else:
            errors.extend(content_errors(rel, head))
        if truncated:
            print(f"PARTIAL text safety scan (first {MAX_SCAN_BYTES} bytes only): {rel}", file=sys.stderr)
        if is_vendored(rel) or truncated:
            continue
        text: str | None = None
        if path.suffix.lower() in TEXT_EXT:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                pass
        if text is None:
            continue
        errors.extend(line_ending_errors(rel, text))
        # Preserve read_text()'s historical formatting/parsing semantics only
        # after checking the original line endings.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
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
        ("secrets.env", "TOKEN = \"sk-" + "abcdefghijklmnopqrstuvwxyz123456\"", "OpenAI-style key"),
        ("config", "api_key = \"sk-" + "abcdefghijklmnopqrstuvwxyz\"", "OpenAI-style key"),
        ("keys/key.pem", "-----BEGIN " + "RSA PRIVATE KEY-----", "private key material"),
    )
    path_failures = path_contract_errors(
        {"sessions/run.jsonl", "skills/.system/tool/SKILL.md", "skills/.other/inside.txt"}
    )
    artifacts_caught = any("runtime/session artifact" in item for item in path_failures)
    vendor_caught = any("vendor runtime" in item and ".other" in item for item in path_failures)
    if not artifacts_caught or not vendor_caught:
        print(f"selftest failed for tracked-path exclusions: {path_failures}", file=sys.stderr)
        return 1
    for rel, text, expected in cases:
        found = content_errors(rel, text)
        if (expected is None and found) or (expected and not any(expected in item for item in found)):
            print(f"selftest failed for {rel}: {found}", file=sys.stderr)
            return 1
    if path_contract_errors({"skills/math-schema/lean/.gitignore"}):
        print("selftest failed: tracked dotfile must not be flagged as vendor runtime", file=sys.stderr)
        return 1
    if content_errors("keys/pub.txt", "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample user@host"):
        print("selftest failed: public SSH key must not be flagged", file=sys.stderr)
        return 1
    if content_errors("compose.yml", "password: ${DB_PASSWORD}\n"):
        print("selftest failed: env placeholder must not be flagged", file=sys.stderr)
        return 1
    endings = (
        ("mixed.md", "line1\r\nline2\nline3\r\n", ["mixed line endings: mixed.md"]),
        ("crlf.md", "a\r\nb\r\n", []),
        ("cr.md", "a\rb\r", []),
    )
    for rel, text, expected in endings:
        found = line_ending_errors(rel, text)
        if found != expected:
            print(f"selftest failed for line endings {rel}: {found}", file=sys.stderr)
            return 1
    if large_file_error("skills/demo/references/sdk/big.md", MAX_BYTES + 1) is None:
        print("selftest failed: large vendored file must be flagged", file=sys.stderr)
        return 1
    if large_file_error("skills/demo/references/sdk/browser_protocol.json", MAX_BYTES + 1) is not None:
        print("selftest failed: exempted SDK file must not be flagged", file=sys.stderr)
        return 1
    if decodable_head(b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 4) is not None:
        print("selftest failed: binary head must not decode", file=sys.stderr)
        return 1
    if decodable_head("caf\u00e9".encode("utf-8")) != "caf\u00e9":
        print("selftest failed: utf-8 head must decode", file=sys.stderr)
        return 1
    if decodable_head("abc\u00e9".encode("utf-8")[:4], truncated=True) != "abc":
        print("selftest failed: split multibyte boundary must decode", file=sys.stderr)
        return 1
    print("REPOSITORY HYGIENE SELFTEST PASS")
    return 0


def _git_commit(root: Path) -> None:
    fixture_git(root, "init", "-q")
    fixture_git(root, "add", "-A")
    fixture_git(root, "commit", "-qm", "fixture")


def _make_repo(root: Path, files: dict[str, bytes]) -> Path:
    root.mkdir(parents=True)
    for rel, blob in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    (root / "scripts").mkdir()
    shutil.copy2(Path(__file__), root / "scripts" / "repo-hygiene.py")
    shutil.copy2(Path(__file__).with_name("publication_fixtures.py"), root / "scripts" / "publication_fixtures.py")
    _git_commit(root)
    return root


def _required_scaffold() -> dict[str, bytes]:
    text = b"fixture\n"
    return {
        "AGENTS.md": text,
        "README.md": text,
        "CONTRIBUTING.md": text,
        "SECURITY.md": text,
        "prompts/.keep": text,
        "templates/agents.md": text,
        "templates/project-context.md": text,
        "templates/roadmap.md": text,
        "templates/readme.md": text,
        "templates/pull-request.md": text,
        "templates/github-pr-ci.yml": b"on: []\n",
        "templates/skill.md": text,
        "mcp/servers.json": b'{"mcpServers":{}}\n',
        "mcp/profiles.json": b"{}\n",
        "mcp/configure.py": b'print("fixture")\n',
        "skills/demo/SKILL.md": text,
    }


def fixture_test() -> int:
    """Integration gate: committed defect repo fails, clean repo passes."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("fixture-test requires PyYAML (same as maintainer validation)", file=sys.stderr)
        return 1
    scaffold = _required_scaffold()
    defect = dict(scaffold)
    defect.update(
        {
            "sessions/run.jsonl": b"{}\n",
            "secrets.env": ("TOKEN = \"sk-" + "abcdefghijklmnopqrstuvwxyz123456\"\n").encode(),
            "key.pem": ("-----BEGIN " + "RSA PRIVATE KEY-----\nabc\n").encode(),
            "notes.md": ("token = \"sk-" + "abcdefghijklmnopqrstuvwxyz123456\"\n").encode(),
            "mixed.md": b"line1\r\nline2\nline3\r\n",
            "widget.tsx": ("const k = \"sk-" + "abcdefghijklmnopqrstuvwxyz123456\";\n").encode(),
            "extensionless-config": ("api_key = \"sk-" + "abcdefghijklmnopqrstuvwxyz\"\n").encode(),
            "skills/.other/inside.txt": b"internal\n",
            "skills/demo/references/private.md": ("-----BEGIN " + "OPENSSH PRIVATE KEY-----\nabc\n").encode(),
            "skills/demo/references/sdk/big.md": b"x" * (MAX_BYTES + 1),
            "mcp/profiles.json": b"not json\n",
        }
    )
    token = "ghp_" + "a" * 30
    for rel in ("github.md", "github.env", "github.tsx", "github-config"):
        defect[rel] = (token + "\n").encode()
    defect["late-token"] = b"a\n" * (160 * 1024) + (token + "\n").encode()
    defect["unsupported.md"] = b"\xff\xfe"
    defect["secret.yaml"] = ("[\n" + token + "\n").encode()
    clean = dict(scaffold)
    clean.update(
        {
            # False-positive controls: public key, env placeholder, uniform CRLF.
            "keys.txt": b"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample user@host\n",
            "compose.yml": b"password: ${DB_PASSWORD}\n",
            "crlf-only.md": b"a\r\nb\r\n",
            "lf-only.md": b"a\nb\n",
            "cr-only.md": b"a\rb\r",
            "binary.dat": b"\0\xff\x89",
            "unknown-encoding": b"\xff\xfe",
        }
    )
    expected = (
        "runtime/session artifact",
        "OpenAI-style key in notes.md",
        *(f"GitHub token in {rel}" for rel in ("github.md", "github.env", "github.tsx", "github-config", "late-token", "secret.yaml")),
        "unsupported text encoding: unsupported.md",
        "private key material in key.pem",
        "private key material in skills/demo/references/private.md",
        "OpenAI-style key in secrets.env",
        "OpenAI-style key in widget.tsx",
        "OpenAI-style key in extensionless-config",
        "mixed line endings: mixed.md",
        "vendor runtime files must not be tracked under skills/",
        "large file (1024KB > 1024KB): skills/demo/references/sdk/big.md",
        "invalid JSON: mcp/profiles.json",
    )
    with tempfile.TemporaryDirectory(prefix="repo-hygiene-fixture-") as tmp:
        defect_root = _make_repo(Path(tmp) / "defect", defect)
        run = subprocess.run(
            [sys.executable, "scripts/repo-hygiene.py"], cwd=defect_root, env=fixture_environment(defect_root),
            capture_output=True, text=True,
        )
        if run.returncode != 1:
            print(f"fixture-test failed: defect repo exit {run.returncode}\n{run.stdout}", file=sys.stderr)
            return 1
        missing = [item for item in expected if item not in run.stdout]
        if missing:
            print(f"fixture-test failed: defect classes not detected: {missing}\n{run.stdout}", file=sys.stderr)
            return 1
        require(token not in run.stdout + run.stderr, "diagnostic leaked credential payload")
        require("PARTIAL text safety scan" in run.stderr, "partial-scan diagnostic missing")
        require("SKIP text safety scan" in run.stderr, "skipped-scan diagnostic missing")
        clean_root = _make_repo(Path(tmp) / "clean", clean)
        run = subprocess.run(
            [sys.executable, "scripts/repo-hygiene.py"], cwd=clean_root, env=fixture_environment(clean_root),
            capture_output=True, text=True,
        )
        if run.returncode != 0:
            print(f"fixture-test failed: clean repo exit {run.returncode}\n{run.stdout}", file=sys.stderr)
            return 1
        require("SKIP text safety scan" in run.stderr, "skipped-scan diagnostic missing")
        # Check the production read boundary, not just the decoding helper.
        from unittest.mock import patch
        with patch.dict(globals(), BASE=clean_root), patch.object(
            Path, "read_bytes", side_effect=AssertionError("unbounded read")
        ):
            errors = check([clean_root / "scripts/repo-hygiene.py"])
        require(not errors, f"bounded-read check failed: {errors}")
    print("REPOSITORY HYGIENE FIXTURE TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--fixture-test", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.fixture_test:
        return fixture_test()
    errors = check(tracked_paths())
    for error in errors[:100]:
        print(f"FAIL  {error}")
    if len(errors) > 100:
        print(f"FAIL  ... {len(errors) - 100} more")
    print(f"REPOSITORY CONTRACTS: {len(errors)} fail")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
