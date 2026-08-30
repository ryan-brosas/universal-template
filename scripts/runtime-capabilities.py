#!/usr/bin/env python3
"""runtime-capabilities.py — probe the installed toolchain; never guess from docs.

Use for setup, debugging environment drift, bootstrap validation, and audits.
NOT part of the per-task hot path. Runtime facts belong here (or to machine-local
config), not frozen into portable philosophy or skills.

Diagnostic only: always exits 0 (unless --smoke fails). Zero dependencies.
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
results: list[tuple[str, str, str]] = []  # (status, name, detail)


def run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def probe(name: str, ok: bool, detail: str = "") -> None:
    results.append(("OK     " if ok else "MISSING", name, detail))


def first_line(text: str) -> str:
    return text.splitlines()[0][:100] if text else ""


# --- CLI tools ---------------------------------------------------------------
rc, out = run(["gh", "--version"])
probe("gh CLI", rc == 0, first_line(out))
rc, out = run(["gh", "auth", "status"])
probe("gh auth", rc == 0, next((l for l in out.splitlines() if "Logged in" in l), "not authenticated"))
rc, out = run(["pi", "--version"], timeout=30)
probe("pi CLI", rc == 0, first_line(out))
rc, out = run(["veda", "--version"], timeout=30)
probe("veda CLI", rc == 0, first_line(out))
rc, out = run(["which", "agy"])
probe("agy CLI", rc == 0, first_line(out) if rc == 0 else "not installed (AGY via veda backend only)")
rc, out = run(["which", "fovea"])
probe("fovea headless CLI", rc == 0, "on PATH" if rc == 0 else "not on PATH (pi-fovea extension still provides graph tools)")
rc, out = run(["which", "devrig"])
probe("mcp-steroid devrig", rc == 0, "on PATH (JetBrains-local bridge)" if rc == 0 else "not on PATH")
rc, out = run(["which", "codebase-memory-mcp"])
probe("codebase-memory-mcp", rc == 0, "on PATH" if rc == 0 else "not on PATH")
rc, out = run(["which", "openviking"])
probe("openviking CLI", rc == 0, "on PATH" if rc == 0 else "not on PATH")

# --- Services ----------------------------------------------------------------
try:
    with urllib.request.urlopen("http://127.0.0.1:1933/mcp", timeout=3) as resp:
        probe("openviking daemon (127.0.0.1:1933)", True, f"HTTP {resp.status}")
except urllib.error.HTTPError as exc:
    probe("openviking daemon (127.0.0.1:1933)", True, f"reachable (HTTP {exc.code}; MCP handshake needed for content)")
except Exception as exc:
    probe("openviking daemon (127.0.0.1:1933)", False, f"unreachable: {type(exc).__name__}")

# --- Installed pi-fabric ------------------------------------------------------
fab_pkg = HOME / ".pi/agent/npm/node_modules/pi-fabric/package.json"
if fab_pkg.is_file():
    try:
        ver = json.loads(fab_pkg.read_text()).get("version", "?")
        docs = (fab_pkg.parent / "docs" / "agents.md").is_file()
        probe("pi-fabric", True, f"v{ver}; docs {'present' if docs else 'MISSING'} (prewalk/schema/veda-runner semantics: read docs/agents.md, docs/schema-enforcement.md)")
    except Exception as exc:
        probe("pi-fabric", False, str(exc))
else:
    probe("pi-fabric", False, f"not found at {fab_pkg}")

# --- Veda model discovery (runtime, never hard-coded) -------------------------
rc, out = run(["veda", "personas"], timeout=60)
probe("veda personas", rc == 0, first_line(out))
rc, out = run(["veda", "models"], timeout=60)
if rc == 0:
    backends = [l.strip() for l in out.splitlines() if l.strip().endswith("(installed)")]
    probe("veda models", True, "; ".join(b.split()[0] for b in backends) + " (full catalog: veda models <backend>)")
else:
    probe("veda models", False, first_line(out))
if (HOME / ".local/bin/agy").exists() or run(["which", "agy"])[0] == 0:
    rc2, out2 = run(["agy", "models"], timeout=60)
    probe("agy models", rc2 == 0, first_line(out2) if rc2 == 0 else "no output")

# --- Harness model/discovery inventory -----------------------------------------
rc, out = run(["pi", "--list-models"], timeout=60)
if rc == 0:
    counts = {}
    for line in out.splitlines()[1:]:
        parts = line.split()
        if parts:
            counts[parts[0]] = counts.get(parts[0], 0) + 1
    total = sum(counts.values())
    top = ", ".join(f"{k}({v})" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:8])
    probe("pi model inventory", True, f"{total} models across {len(counts)} providers: {top}")
else:
    probe("pi model inventory", False, first_line(out))
for backend in ("claude", "codex", "gemini", "droid"):
    rc, out = run(["which", backend])
    probe(f"backend CLI: {backend}", rc == 0, "on PATH" if rc == 0 else "absent (unavailable as a direct/Veda backend)")
rc, out = run(["which", "fabric"])
if rc == 0:
    results.append(("UNKNOWN", "fabric native runners", "CLI on PATH; runner/model inventory is session state — probe in-session via agents.models()/agents.list() (often empty); do not assume"))
else:
    results.append(("UNKNOWN", "fabric native runners", "fabric CLI not on PATH from here — runner availability unknown; probe in-session"))

# --- MCP registry state -------------------------------------------------------
reg = HOME / ".agents/mcp/servers.json"
try:
    servers = json.loads(reg.read_text())["mcpServers"]
    abs_paths = [n for n, c in servers.items() if str(c.get("command", "")).startswith("/")]
    probe("mcp registry", True, f"{len(servers)} servers: {', '.join(servers)}" + (f" | WARN absolute commands: {abs_paths}" if abs_paths else ""))
except Exception as exc:
    probe("mcp registry", False, str(exc))

# --- Machine-local configuration warnings -------------------------------------
for rel in (".pi/", ".idea/"):
    rc, out = run(["git", "-C", str(HOME / ".agents"), "check-ignore", "-q", rel])
    if rc != 0:
        results.append(("WARN   ", f"{rel} not gitignored", "machine-local state must stay out of the repo"))
if "CBM_CACHE_DIR" in reg.read_text() if reg.is_file() else False:
    results.append(("WARN   ", "CBM_CACHE_DIR is machine-local", "env value points at this workstation's cache; fine for live wiring, not portable"))

# --- Fabric Veda runner smoke (opt-in; a real agents.run boundary is heavier) --
smoke_failed = False
if "--smoke" in sys.argv:
    rc, out = run(["veda", "-S", "cap-probe", "-b", "agy", "-m", "gemini-flash", "--no-tools",
                   "-o", "/tmp/veda-smoke-out.md", "Reply with the single word OK"], timeout=120)
    body = Path("/tmp/veda-smoke-out.md").read_text()[:120] if Path("/tmp/veda-smoke-out.md").exists() else ""
    smoke_ok = rc == 0 and "OK" in body.upper()
    smoke_failed = not smoke_ok
    probe("veda one-shot smoke (agy/gemini-flash)", smoke_ok, first_line(body) or first_line(out))
    print("NOTE: Fabric-side agents.run({runner:'veda'}) hands off at the outer fabric_exec boundary;")
    print("      probe it live in a session if the direct CLI works but Fabric delegation does not.")

for status, name, detail in results:
    print(f"{status}  {name:38s} {detail}")
print("runtime-capabilities: diagnostic only; runtime facts stay here, philosophy stays in docs")
sys.exit(1 if smoke_failed else 0)
