#!/usr/bin/env python3
"""resolve-model.py — deterministic role → backend/model resolution.

Mechanical counterpart of skills/model-resolution. Discovers what exists NOW
(pi --list-models, veda models, which), applies the role's hard filters, ranks
survivors by config/model-profiles.yaml preference order, and prints
candidates plus excluded reasons. Zero dependencies; machine-readable by
default so agents parse instead of re-deriving.

Exits 0 whenever a valid report is produced (even with zero candidates);
exit 2 only on bad usage. Auth is NOT probed by default (environment-scoped);
--probe runs a one-shot smoke against the top candidate.

Usage:
  resolve-model.py --role REVIEWER [--json]
  resolve-model.py --role WORKER --require-context 128000 --backend agy
  resolve-model.py --roles           # list known roles
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()


def profiles_path() -> Path:
    """Preference file: explicit AGENTS_PROFILES override → the checkout this
    script lives in → the installed ~/.agents tree (legacy fallback)."""
    env = os.environ.get("AGENTS_PROFILES")
    if env:
        return Path(env)
    local = Path(__file__).resolve().parents[1] / "config/model-profiles.yaml"
    if local.is_file():
        return local
    return HOME / ".agents/config/model-profiles.yaml"


# role → (min_context_tokens, requires_images, profile_lanes)
ROLE_REQS: dict[str, tuple[int, bool, list[str]]] = {
    "MAIN":                   (32_000, False, ["economy-worker"]),
    "WORKER":                 (32_000, False, ["economy-worker", "spam-worker"]),
    "REFERENCE-INVESTIGATOR": (64_000, False, ["fast-investigator"]),
    "REVIEWER":               (128_000, False, ["strong-reviewer"]),
    "SECURITY-REVIEWER":      (128_000, False, ["strong-reviewer"]),
    "NAVIGATOR":              (128_000, False, ["architect"]),
    "SOLVER":                 (128_000, False, ["architect"]),
    "JUDGE":                  (128_000, False, ["architect"]),
    "VERIFIER":               (128_000, False, ["architect"]),
    "FRONTEND-CRITIC":        (64_000, True,  ["frontend-critic"]),
    "DEBUGGER":               (32_000, False, ["debugger"]),
    "SUPERVISOR":             (64_000, False, ["fast-investigator"]),
}


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def parse_ctx(token: str) -> int | None:
    m = re.fullmatch(r"([\d.]+)\s*([KM]?)", token.strip(), re.I)
    if not m:
        return None
    val = float(m.group(1))
    mult = {"": 1, "K": 1_000, "M": 1_000_000}[m.group(2).upper()]
    return int(val * mult)


def load_profiles() -> dict[str, list[str]]:
    """Parse the `profiles:` section (indentation-based YAML subset)."""
    out: dict[str, list[str]] = {}
    prof = profiles_path()
    if not prof.is_file():
        return out
    lane: str | None = None
    in_prefer = False
    for raw in prof.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(\s*)([A-Za-z0-9_-]+):(.*)$", line)
        if m and not line.startswith("      "):
            indent, key, rest = m.groups()
            if indent == "":
                in_prefer = key == "profiles"
                lane = None
                continue
            if in_prefer and indent == "  ":
                lane = key
                out.setdefault(lane, [])
                in_prefer = True
                continue
        m2 = re.match(r"^\s*-\s*(\S+)", line)
        if m2 and lane and in_prefer:
            out[lane].append(m2.group(1))
    return out


def discover_pi() -> tuple[list[dict], list[str]]:
    rc, out = run(["pi", "--list-models"], timeout=60)
    if rc != 0:
        return [], [f"pi --list-models unavailable: {out[:80]}"]
    entries: list[dict] = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        provider, model = parts[0], parts[1]
        ctx = parse_ctx(parts[2])
        flags = {p.lower() for p in parts[4:]}
        entries.append({
            "backend": "pi", "provider": provider, "model": model,
            "address": f"pi:{provider}/{model}",
            "context_tokens": ctx,
            "thinking": "yes" in flags, "images": "yes" in flags,
            "source": "pi --list-models",
        })
    return entries, []


def discover_veda() -> tuple[list[dict], list[str]]:
    rc, out = run(["veda", "models"], timeout=60)
    if rc != 0:
        return [], [f"veda models unavailable: {out[:80]}"]
    backends = [l.split()[0] for l in out.splitlines() if l.strip().endswith("(installed)")]
    entries: list[dict] = []
    for backend in backends:
        rc2, out2 = run(["veda", "models", backend], timeout=60)
        if rc2 != 0:
            continue
        seen: set[str] = set()
        in_models = False
        for line in out2.splitlines():
            s = line.strip()
            if s.startswith("models ("):
                in_models = True
                continue
            if s.startswith("aliases"):
                in_models = False
                continue
            m_def = re.match(r"^default\s+(\S+)", s)
            if m_def:
                seen.add(m_def.group(1))
                continue
            m_alias = re.match(r"^\S+\s+→\s+(\S+?)(?:\s+\[|\s*$)", s)
            if m_alias:
                seen.add(m_alias.group(1))
                continue
            if in_models and s and not s.startswith("("):
                seen.add(s.split()[0])
        for model in sorted(seen):
            entries.append({
                "backend": backend, "provider": backend, "model": model,
                "address": f"{backend}:{model}",
                "context_tokens": None, "thinking": None, "images": None,
                "source": f"veda models {backend}",
            })
    return entries, []


def resolve(role: str, require_context: int | None, require_images: bool,
           require_thinking: bool, backend: str | None, limit: int) -> dict:
    notes: list[str] = []
    if role not in ROLE_REQS:
        raise SystemExit(f"unknown role: {role} (known: {', '.join(sorted(ROLE_REQS))})")
    min_ctx, want_images, lanes = ROLE_REQS[role]
    if require_context:
        min_ctx = require_context
    if require_images:
        want_images = True

    profiles = load_profiles()
    chain: list[str] = []
    for lane in lanes:
        chain.extend(profiles.get(lane, []))

    candidates: list[dict] = []
    excluded: list[dict] = []
    pi_entries, pi_notes = discover_pi()
    notes.extend(pi_notes)
    veda_entries, veda_notes = discover_veda()
    notes.extend(veda_notes)

    def rank_key(e: dict) -> tuple:
        pref = len(chain)
        for i, addr in enumerate(chain):
            base = addr.split(":", 1)[1] if ":" in addr else addr
            if addr in (e["address"],) or base == e["model"] or e["address"].endswith(base):
                pref = i
                break
        return (pref, -(e["context_tokens"] or 0))

    for e in pi_entries + veda_entries:
        reasons: list[str] = []
        if backend and e["backend"] != backend:
            reasons.append(f"backend != {backend}")
        if e["context_tokens"] is not None and e["context_tokens"] < min_ctx:
            reasons.append(f"context {e['context_tokens']} < {min_ctx}")
        # Unknown context is NOT an exclusion: several discovery surfaces (veda
        # backends) do not report context. Keep the candidate, flag it, and let
        # the preference chain rank it; the report marks it context_unverified.
        if want_images and e["images"] is False:
            reasons.append("no image support")
        if require_thinking and e["thinking"] is False:
            reasons.append("no thinking support")
        if reasons:
            excluded.append({"address": e["address"], "reasons": reasons})
        else:
            if e["context_tokens"] is None:
                e["context_unverified"] = True
            if e.get("thinking") is None or e.get("images") is None:
                e["capability_unverified"] = True
            candidates.append(e)
    candidates.sort(key=rank_key)
    candidates = candidates[:limit]

    chosen = candidates[0]["address"] if candidates else None
    report = {
        "role": role,
        "requirements": {"min_context": min_ctx, "images": want_images,
                         "thinking": require_thinking or None,
                         "backend": backend, "profile_lanes": lanes},
        "preference_chain": chain,
        "chosen": chosen,
        "candidates": [{**{k: e[k] for k in ("address", "backend", "model",
                                             "context_tokens", "thinking",
                                             "images", "source")},
                        "context_unverified": e.get("context_unverified", False),
                        "capability_unverified": e.get("capability_unverified", False)}
                       for e in candidates],
        "excluded": excluded[:40],
        "auth": "NOT PROBED (environment-scoped; use --probe for a one-shot smoke)",
        "notes": notes,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return report


def probe(report: dict) -> str | None:
    if not report["candidates"]:
        return None
    top = report["candidates"][0]
    if top["backend"] == "pi":
        model = f"pi/{top['address'].split(':', 1)[1]}"
        cmd = ["veda", "-S", "resolve-probe", "-b", "pi", "-m", model,
               "--no-tools", "-o", "/tmp/resolve-probe.md", "Reply with the single word OK"]
    else:
        cmd = ["veda", "-S", "resolve-probe", "-b", top["backend"], "-m", top["model"],
               "--no-tools", "-o", "/tmp/resolve-probe.md", "Reply with the single word OK"]
    rc, out = run(cmd, timeout=120)
    body = ""
    if Path("/tmp/resolve-probe.md").is_file():
        body = Path("/tmp/resolve-probe.md").read_text()[:120]
    ok = rc == 0 and "OK" in body.upper()
    return ("PASS" if ok else "FAIL") + f" ({top['address']}): {(body or out)[:80]}"


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--role")
    ap.add_argument("--require-context", type=int, default=None)
    ap.add_argument("--require-images", action="store_true")
    ap.add_argument("--require-thinking", action="store_true")
    ap.add_argument("--backend", default=None)
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable output (the default)")
    ap.add_argument("--table", action="store_true")
    ap.add_argument("--roles", action="store_true")
    args = ap.parse_args()
    if args.roles:
        print("\n".join(sorted(ROLE_REQS)))
        return 0
    if not args.role:
        ap.error("--role is required (or --roles)")
    args.role = args.role.upper()  # roles are canonical uppercase; accept any case
    report = resolve(args.role, args.require_context, args.require_images,
                     args.require_thinking, args.backend, args.limit)
    if args.probe:
        report["probe"] = probe(report)
    if args.table:
        print(f"role={report['role']} chosen={report['chosen']}")
        for c in report["candidates"]:
            ctx = c["context_tokens"] if c["context_tokens"] is not None else "?"
            print(f"  {c['address']:55s} ctx={ctx}")
        for e in report["excluded"][:10]:
            print(f"  EXCLUDED {e['address']:47s} {', '.join(e['reasons'])}")
        for n in report["notes"]:
            print(f"  NOTE {n}")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
