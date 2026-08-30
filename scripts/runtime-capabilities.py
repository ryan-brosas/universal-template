#!/usr/bin/env python3
"""runtime-capabilities.py — probe the installed toolchain; never guess from docs.

Use for setup, debugging environment drift, bootstrap validation, and audits.
NOT part of the per-task hot path. Runtime facts belong here (or to machine-local
state), not frozen into portable philosophy or skills.

Output: human table by default, machine-readable JSON with --json.
Smoke test: --smoke [backend] — provider-neutral one-shot probe; the default
backend resolves from config/model-profiles.yaml (economy-worker chain).

Diagnostic only: always exits 0 (unless a smoke run fails). Zero dependencies.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
AGENTS = HOME / ".agents"
records: list[dict] = []  # {status, name, detail}


def run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def probe(name: str, ok: bool, detail: str = "") -> None:
    records.append({"status": "OK" if ok else "MISSING", "name": name, "detail": detail})


def note(name: str, detail: str, status: str = "UNKNOWN") -> None:
    records.append({"status": status, "name": name, "detail": detail})


def first_line(text: str) -> str:
    return text.splitlines()[0][:100] if text else ""


def load_smoke_chain() -> list[str]:
    """Preference chain for the default smoke target (stable prefs only)."""
    pref = AGENTS / "config/model-profiles.yaml"
    chain: list[str] = []
    if pref.is_file():
        in_lane = False
        for raw in pref.read_text().splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if line.strip() == "economy-worker:":
                in_lane = True
                continue
            if in_lane and re.match(r"^\s*-\s*(\S+)", line):
                chain.append(re.match(r"^\s*-\s*(\S+)", line).group(1))
            elif in_lane and line and not line.startswith(" "):
                break
    return chain


def pick_smoke_target(backend_arg: str | None) -> tuple[str, str, str]:
    """Return (invocation, backend, model). invocation: 'veda-pi' | 'veda-direct'."""
    chain = load_smoke_chain()
    wanted = [backend_arg] if backend_arg and backend_arg != "auto" else None
    for entry in chain:
        if ":" not in entry:
            continue
        backend, model = entry.split(":", 1)
        if wanted and backend != wanted[0]:
            continue
        if backend == "pi":
            rc, out = run(["pi", "--list-models"], timeout=60)
            provider, _, mpart = model.partition("/")
            if rc == 0 and any(l.split()[:2] == [provider, mpart] for l in out.splitlines() if len(l.split()) >= 2):
                return "veda-pi", "pi", f"pi/{model}"
        else:
            rc, out = run(["veda", "models", backend], timeout=60)
            if rc == 0 and model in out:
                return "veda-direct", backend, model
    # Fallbacks: explicit backend via veda default, else agy default.
    if wanted:
        rc, out = run(["veda", "models", wanted[0]], timeout=60)
        if rc == 0:
            m = re.search(r"^\s*default\s+(\S+)", out, re.M)
            if m:
                return "veda-direct", wanted[0], m.group(1)
    rc, out = run(["veda", "models", "agy"], timeout=60)
    if rc == 0:
        m = re.search(r"^\s*default\s+(\S+)", out, re.M)
        if m:
            return "veda-direct", "agy", m.group(1)
    return "veda-direct", "agy", "gemini-flash"


def collect() -> None:
    # --- CLI tools -------------------------------------------------------------
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

    # --- Services --------------------------------------------------------------
    try:
        with urllib.request.urlopen("http://127.0.0.1:1933/mcp", timeout=3) as resp:
            probe("openviking daemon (127.0.0.1:1933)", True, f"HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        probe("openviking daemon (127.0.0.1:1933)", True, f"reachable (HTTP {exc.code}; MCP handshake needed for content)")
    except Exception as exc:
        probe("openviking daemon (127.0.0.1:1933)", False, f"unreachable: {type(exc).__name__}")

    # --- Installed pi-fabric ----------------------------------------------------
    fab_pkg = HOME / ".pi/agent/npm/node_modules/pi-fabric/package.json"
    if fab_pkg.is_file():
        try:
            ver = json.loads(fab_pkg.read_text()).get("version", "?")
            docs = (fab_pkg.parent / "docs" / "agents.md").is_file()
            probe("pi-fabric", True, f"v{ver}; docs {'present' if docs else 'MISSING'} (runner/RLM/schema semantics: read docs/agents.md, docs/schema-enforcement.md)")
        except Exception as exc:
            probe("pi-fabric", False, str(exc))
    else:
        probe("pi-fabric", False, f"not found at {fab_pkg}")

    # --- Veda model discovery (runtime, never hard-coded) -----------------------
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

    # --- Harness model/discovery inventory --------------------------------------
    rc, out = run(["pi", "--list-models"], timeout=60)
    if rc == 0:
        counts: dict[str, int] = {}
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
        note("fabric native runners", "CLI on PATH; runner/model inventory is session state — probe in-session via agents.models()/agents.list() (often empty); do not assume")
    else:
        note("fabric native runners", "fabric CLI not on PATH from here — runner availability unknown; probe in-session")

    # --- MCP registry state ------------------------------------------------------
    reg = AGENTS / "mcp/servers.json"
    try:
        servers = json.loads(reg.read_text())["mcpServers"]
        abs_paths = [n for n, c in servers.items() if str(c.get("command", "")).startswith("/")]
        probe("mcp registry", True, f"{len(servers)} servers: {', '.join(servers)}" + (f" | WARN absolute commands: {abs_paths}" if abs_paths else ""))
    except Exception as exc:
        probe("mcp registry", False, str(exc))

    # --- Machine-local configuration warnings ------------------------------------
    for rel in (".pi/", ".idea/"):
        rc, out = run(["git", "-C", str(AGENTS), "check-ignore", "-q", rel])
        if rc != 0:
            note(f"{rel} not gitignored", "machine-local state must stay out of the repo", "WARN")
    if reg.is_file() and "CBM_CACHE_DIR" in reg.read_text():
        note("CBM_CACHE_DIR is machine-local", "env value points at this workstation's cache; fine for live wiring, not portable", "WARN")


def smoke(backend_arg: str | None) -> dict:
    invocation, backend, model = pick_smoke_target(backend_arg)
    if invocation == "veda-pi":
        cmd = ["veda", "-S", "cap-probe", "-b", "pi", "-m", model, "--no-tools",
               "-o", "/tmp/veda-smoke-out.md", "Reply with the single word OK"]
    else:
        cmd = ["veda", "-S", "cap-probe", "-b", backend, "-m", model, "--no-tools",
               "-o", "/tmp/veda-smoke-out.md", "Reply with the single word OK"]
    rc, out = run(cmd, timeout=120)
    body = Path("/tmp/veda-smoke-out.md").read_text()[:120] if Path("/tmp/veda-smoke-out.md").is_file() else ""
    ok = rc == 0 and "OK" in body.upper()
    result = {"backend": backend, "model": model, "ok": ok,
              "detail": first_line(body) or first_line(out)}
    probe(f"one-shot smoke ({backend}/{model})", ok, result["detail"])
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--smoke", nargs="?", const="auto", default=None, metavar="BACKEND",
                    help="one-shot smoke probe; optional backend (pi, agy, codex, claude-code, droid). Default resolves from model-profiles.yaml")
    args = ap.parse_args()

    collect()
    smoke_result = None
    if args.smoke is not None:
        smoke_result = smoke(args.smoke)
        print("NOTE: Fabric-side agents.run({runner:'veda'}) hands off at the outer fabric_exec boundary;")
        print("      probe it live in a session if the direct CLI works but Fabric delegation does not.")

    if args.json:
        print(json.dumps({
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "probes": records,
            "smoke": smoke_result,
        }, indent=2))
    else:
        for r in records:
            print(f"{r['status']:7s}  {r['name']:38s} {r['detail']}")
        print("runtime-capabilities: diagnostic only; runtime facts stay here, philosophy stays in docs")
    return 0 if (smoke_result is None or smoke_result["ok"]) else 1


if __name__ == "__main__":
    sys.exit(main())
