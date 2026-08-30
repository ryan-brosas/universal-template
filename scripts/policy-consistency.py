#!/usr/bin/env python3
"""policy-consistency.py — deterministic policy drift gate for universal-template.

This file is the SINGLE machine-readable enumeration of cross-document policy
invariants. Each check below states one invariant; do not restate policy in a
second hand-maintained philosophy document — add or extend a check here.

Scope: policy documents only (AGENTS, README, essentials, routing/workflow
skills, mcp registry, PR template). Foundation capsules with pinned provenance
and verbatim archives (essentials/discord-material) are exempt by design.

FAIL = exit 1 (CI gate). WARN = printed, non-blocking.
Zero dependencies; python3 stdlib only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

# essentials/*.md is policy as a set (globbed below) — new essentials docs are covered automatically.
POLICY_FILES = [
    "AGENTS.md",
    "README.md",
    "skills/evidence-router/SKILL.md",
    "skills/codebase-driven-development/SKILL.md",
    "skills/code-foundations/SKILL.md",
    "skills/codebase-memory/SKILL.md",
    "skills/fabric-native-execution/SKILL.md",
    "skills/veda-lane/SKILL.md",
    "skills/execution-router/SKILL.md",
    "skills/model-resolution/SKILL.md",
    "skills/workflow-lifecycle/SKILL.md",
    "skills/foundations-workflow/SKILL.md",
    "skills/github-repo-setup/SKILL.md",
    "skills/leverage-playbook/references/session-principles.md",
]
POLICY_FILES += sorted(str(p.relative_to(BASE)) for p in (BASE / "essentials").glob("*.md"))

fails: list[str] = []
warns: list[str] = []


def read(rel: str) -> str | None:
    p = BASE / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def check_fail(cid: str, rel: str, line_no: int, detail: str) -> None:
    fails.append(f"[{cid}] {rel}:{line_no}: {detail}")


def forbid_phrase(cid: str, phrase: str, files: list[str] | None = None) -> None:
    for rel in (files or POLICY_FILES):
        text = read(rel)
        if not text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if phrase.lower() in line.lower():
                check_fail(cid, rel, i, f"forbidden phrase: {phrase!r}")


def require_phrase(cid: str, rel: str, phrase: str) -> None:
    text = read(rel)
    if text is None:
        fails.append(f"[{cid}] {rel}: file missing")
    elif phrase not in re.sub(r"\s+", " ", text):
        fails.append(f"[{cid}] {rel}: required phrase missing: {phrase!r}")


# --- The invariant registry -------------------------------------------------
# One entry per invariant; keep descriptions imperative.

def check_prewalk_reserved() -> None:
    """'prewalk' in policy docs only with its real Fabric meaning or as marked source wording."""
    allow = re.compile(r"fabric|source wording|source material|mentor", re.I)
    for rel in POLICY_FILES:
        text = read(rel)
        if not text:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not re.search(r"prewalk", line, re.I):
                continue
            context = " ".join(lines[max(0, i - 1): i + 2])  # markdown wraps mid-sentence
            if not allow.search(context):
                check_fail("PREWALK-RESERVED", rel, i + 1, "generic 'prewalk' use (reserved for /fabric prewalk)")


def check_lifecycle_optional() -> None:
    """workflow-lifecycle is opt-in; never a mandatory default loop."""
    for rel in ("AGENTS.md", "README.md"):
        text = read(rel) or ""
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"mandatory default", line, re.I):
                check_fail("LIFECYCLE-OPTIONAL", rel, i, "'mandatory default' loop language")
    require_phrase("LIFECYCLE-OPTIONAL", "AGENTS.md", "Workflow-lifecycle is opt-in")
    require_phrase("LIFECYCLE-OPTIONAL", "skills/workflow-lifecycle/SKILL.md", "one-off")


def check_schema_mode_gated() -> None:
    """The Schema loop is opt-in (enforce mode / explicit request), never the universal mutation gate."""
    for phrase in (
        "stays the mutation gate",
        "must use the Schema loop",
        "Schema loop is mandatory",
        "before any mutation, run the Schema loop",
    ):
        forbid_phrase("SCHEMA-MODE-GATED", phrase)
    require_phrase(
        "SCHEMA-MODE-GATED",
        "skills/fabric-native-execution/SKILL.md",
        "Schema enforce only for intentionally strict transactional mutation",
    )


def check_agents_run_not_banned() -> None:
    """agents.run is a supported escalation (Fabric Veda runner); never globally banned."""
    for rel in ("skills/fabric-native-execution/SKILL.md", "skills/veda-lane/SKILL.md"):
        text = read(rel)
        if not text:
            continue
        if re.search(r"do not dispatch subagents", text, re.I):
            fails.append(f"[AGENTS-RUN-NOT-BANNED] {rel}: bans agents.run dispatch")
        if re.search(r"agents\.run[^\n]{0,120}broken|broken[^\n]{0,120}agents\.run", text, re.I):
            fails.append(f"[AGENTS-RUN-NOT-BANNED] {rel}: hard-codes a broken-runner claim (use runtime probing)")


def check_veda_runtime_discovery() -> None:
    """Veda model/persona availability is runtime-discovered; no hard-coded AGY-hosted Claude."""
    for rel in POLICY_FILES:
        text = read(rel)
        if not text:
            continue
        if "claude-opus-4-6-thinking" in text:
            check_fail("VEDA-RUNTIME-DISCOVERY", rel, 0, "hard-coded AGY-hosted Claude model")
        if "gemini-3.7-flash" in text or "gemini-3.1-pro" in text:
            check_fail("VEDA-RUNTIME-DISCOVERY", rel, 0, "hard-coded concrete model slug (use veda models)")
    require_phrase("VEDA-RUNTIME-DISCOVERY", "skills/veda-lane/SKILL.md", "veda models")


def check_stale_routes() -> None:
    """No stale tool routes (codegraphcontext / ide_idea_*) in policy files."""
    for token in ("codegraphcontext", "ide_idea_"):
        forbid_phrase("STALE-ROUTES", token)


def check_mcp_count() -> None:
    """README's stated MCP server count matches mcp/servers.json."""
    data = read("mcp/servers.json")
    readme = read("README.md") or ""
    try:
        n = len(json.loads(data)["mcpServers"])
    except Exception as exc:
        fails.append(f"[MCP-COUNT] mcp/servers.json unreadable: {exc}")
        return
    claimed = {int(m) for m in re.findall(r"(\d+) servers", readme)}
    if claimed and claimed != {n}:
        fails.append(f"[MCP-COUNT] README claims {sorted(claimed)} servers; registry has {n}")


def check_mcp_portable() -> None:
    """Registry commands resolve via PATH; no absolute /home/ /mnt/ in command or args."""
    data = read("mcp/servers.json")
    try:
        servers = json.loads(data)["mcpServers"]
    except Exception:
        return
    for name, cfg in servers.items():
        for key in ("command", *cfg.get("args", [])):
            val = str(cfg.get("command") if key == "command" else key)
            if val.startswith("/") or "/home/" in val or "/mnt/" in val:
                fails.append(f"[MCP-PORTABLE] servers.json: server {name!r} uses absolute path: {val}")
        for k, v in (cfg.get("env") or {}).items():
            if isinstance(v, str) and (v.startswith("/") or "/mnt/" in v):
                warns.append(f"[MCP-PORTABLE-WARN] servers.json: {name}.env.{k} is machine-local: {v}")


def check_ut_gate_scoped() -> None:
    """universal-template validators are scoped to this repo, never universal."""
    require_phrase("UT-GATE-SCOPED", "AGENTS.md", "repository-specific checks, not a universal requirement")


def check_absolutes() -> None:
    """No model-equivalence / zero-hallucination / always-capture absolutes in policy docs."""
    for phrase in (
        "zero hallucination",
        "mistake-free",
        "unbypassable shortcut",
        "unbypassable skill",
        "Always run a skill-capture pass",
        "guarantee correctness",
        "guarantees deterministic correctness",
    ):
        forbid_phrase("ABSOLUTES", phrase)


def check_portable_paths() -> None:
    """WARN: portable policy docs should not pin machine-specific /home/ or /mnt/ paths."""
    files = ["AGENTS.md", "README.md", *sorted(str(p.relative_to(BASE)) for p in (BASE / "essentials").glob("*.md"))]
    for rel in files:
        text = read(rel)
        if not text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"/home/|/mnt/", line):
                warns.append(f"[PORTABLE-PATHS-WARN] {rel}:{i}: machine-specific path")


def check_pr_template() -> None:
    """PR template uses the core sections and carries no CodeMemory-centric requirements."""
    text = read(".github/pull_request_template.md")
    if text is None:
        fails.append("[PR-TEMPLATE] .github/pull_request_template.md missing")
        return
    for heading in ("## Summary", "## Why", "## Verification", "## Risks"):
        if heading not in text:
            fails.append(f"[PR-TEMPLATE] required heading missing: {heading}")
    if "Codebase observation" in text:
        fails.append("[PR-TEMPLATE] stale CodeMemory-centric section present")


def check_no_mass_ingestion() -> None:
    """Essentials never promise mass ingestion/squeezing of inspiration repos (foundation freeze)."""
    for rel in ("essentials/README.md", "essentials/objectives.md"):
        text = read(rel)
        if text is None:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if "squeeze" in low or re.search(r"100%\s+(inspiration\s+)?ingestion", low) or "full squeeze" in low:
                check_fail("NO-MASS-INGESTION", rel, i, "mass-ingestion promise contradicts the foundation freeze")


def check_router_visibility() -> None:
    """Top-level *-router skills must stay model-visible (they route automatically)."""
    skills_dir = BASE / "skills"
    if not skills_dir.is_dir():
        return
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or not d.name.endswith("-router"):
            continue
        rel = f"skills/{d.name}/SKILL.md"
        text = read(rel)
        if text is None:
            continue
        if re.search(r"^disable-model-invocation:\s*true", text, re.M):
            check_fail("ROUTER-VISIBILITY", rel, 1, "router skill has disable-model-invocation: true — a router must be model-visible")


def check_evidence_router_scope() -> None:
    """evidence-router routes EVIDENCE only: no provider/model selection content."""
    rel = "skills/evidence-router/SKILL.md"
    text = read(rel)
    if text is None:
        return
    banned = re.compile(r"veda\b|\bagy\b|codex|claude|opus|gemini|gpt-|deepseek|qwen|disable-model-invocation", re.I)
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail("EVIDENCE-ROUTER-SCOPE", rel, i, "evidence-router must not carry provider/model selection content")


def check_veda_lane_ownership() -> None:
    """veda-lane is an execution adapter; it never claims global model-routing ownership."""
    rel = "skills/veda-lane/SKILL.md"
    text = read(rel)
    if text is None:
        fails.append(f"[{ 'VEDA-LANE-OWNERSHIP' }] {rel}: file missing")
        return
    flat = re.sub(r"\s+", " ", text)
    if "execution adapter" not in flat:
        check_fail("VEDA-LANE-OWNERSHIP", rel, 1, "veda-lane must frame itself as an execution adapter/oracle lane")
    if "routing layer" in flat or "model-router" in flat:
        check_fail("VEDA-LANE-OWNERSHIP", rel, 1, "veda-lane must not claim model-routing ownership")


def check_profiles_stable_prefs() -> None:
    """config/model-profiles.yaml holds stable preferences only — no dated/auth runtime state."""
    rel = "config/model-profiles.yaml"
    text = read(rel)
    if text is None:
        return
    banned = re.compile(r"20\d\d-\d\d|unauthenticated|/login|broken|auth state", re.I)
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail("PROFILES-STABLE-PREFS", rel, i, "model-profiles.yaml must hold stable preferences only (runtime state goes to state/ or audits/)")


def check_resolver_json() -> None:
    """scripts/resolve-model.py --json produces valid JSON with a candidates list."""
    try:
        p = subprocess.run(["python3", str(BASE / "scripts/resolve-model.py"), "--role", "REVIEWER", "--json"],
                           capture_output=True, text=True, timeout=90)
        data = json.loads(p.stdout)
        if not isinstance(data.get("candidates"), list):
            fails.append("[RESOLVER-JSON] scripts/resolve-model.py: output missing 'candidates' list")
    except Exception as exc:
        fails.append(f"[RESOLVER-JSON] scripts/resolve-model.py: {type(exc).__name__}: {exc}")


def check_runtime_json() -> None:
    """scripts/runtime-capabilities.py --json produces valid JSON with a probes list."""
    try:
        p = subprocess.run(["python3", str(BASE / "scripts/runtime-capabilities.py"), "--json"],
                           capture_output=True, text=True, timeout=120)
        data = json.loads(p.stdout)
        if not isinstance(data.get("probes"), list):
            fails.append("[RUNTIME-JSON] scripts/runtime-capabilities.py: output missing 'probes' list")
    except Exception as exc:
        fails.append(f"[RUNTIME-JSON] scripts/runtime-capabilities.py: {type(exc).__name__}: {exc}")


def check_router_refs_resolve() -> None:
    """skills/<name> references inside router SKILL.md files must exist."""
    for name in ("evidence-router", "execution-router", "model-resolution"):
        rel = f"skills/{name}/SKILL.md"
        text = read(rel)
        if text is None:
            fails.append(f"[ROUTER-REFS-RESOLVE] {rel}: file missing")
            continue
        for m in re.finditer(r"`skills/([a-z0-9-]+)", text):
            if not (BASE / f"skills/{m.group(1)}/SKILL.md").is_file():
                check_fail("ROUTER-REFS-RESOLVE", rel, 1, f"dangling skill reference: skills/{m.group(1)}")



CHECKS = [
    ("PREWALK-RESERVED", check_prewalk_reserved),
    ("LIFECYCLE-OPTIONAL", check_lifecycle_optional),
    ("SCHEMA-MODE-GATED", check_schema_mode_gated),
    ("AGENTS-RUN-NOT-BANNED", check_agents_run_not_banned),
    ("VEDA-RUNTIME-DISCOVERY", check_veda_runtime_discovery),
    ("STALE-ROUTES", check_stale_routes),
    ("MCP-COUNT", check_mcp_count),
    ("MCP-PORTABLE", check_mcp_portable),
    ("UT-GATE-SCOPED", check_ut_gate_scoped),
    ("ABSOLUTES", check_absolutes),
    ("PORTABLE-PATHS", check_portable_paths),
    ("PR-TEMPLATE", check_pr_template),
    ("NO-MASS-INGESTION", check_no_mass_ingestion),
    ("ROUTER-VISIBILITY", check_router_visibility),
    ("EVIDENCE-ROUTER-SCOPE", check_evidence_router_scope),
    ("VEDA-LANE-OWNERSHIP", check_veda_lane_ownership),
    ("PROFILES-STABLE-PREFS", check_profiles_stable_prefs),
    ("RESOLVER-JSON", check_resolver_json),
    ("RUNTIME-JSON", check_runtime_json),
    ("ROUTER-REFS-RESOLVE", check_router_refs_resolve),
]


def main() -> int:
    for _cid, fn in CHECKS:
        fn()
    for w in warns:
        print(f"WARN  {w}")
    for f in fails:
        print(f"FAIL  {f}")
    print(f"POLICY CONSISTENCY: {len(CHECKS)} checks, {len(fails)} fail, {len(warns)} warn")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
