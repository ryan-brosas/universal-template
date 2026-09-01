#!/usr/bin/env python3
"""policy-consistency.py — deterministic policy drift gate for universal-template.

This file is the SINGLE machine-readable enumeration of cross-document policy
invariants. Each check below states one invariant; do not restate policy in a
second hand-maintained philosophy document — add or extend a check here.

Scope: policy documents only (AGENTS, README, essentials, routing/workflow
skills, mcp registry, PR template). Coded prior-art archives and verbatim
archives (foundation-pack/, essentials/discord-material) are exempt by design.

FAIL = exit 1 (CI gate). WARN = printed, non-blocking.
Zero dependencies; python3 stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

BASE = Path(__file__).resolve().parents[1]

# essentials/*.md is policy as a set (globbed below) — new essentials docs are covered automatically.
POLICY_FILES = [
    "AGENTS.md",
    "README.md",
    "skills/evidence-router/SKILL.md",
    "skills/reference-driven-development/SKILL.md",
    "skills/project-bootstrap/SKILL.md",
    "skills/goal-setup/SKILL.md",
    "skills/leverage-capture/SKILL.md",
    "skills/codebase-memory/SKILL.md",
    "skills/fabric-native-execution/SKILL.md",
    "skills/veda-lane/SKILL.md",
    "skills/execution-router/SKILL.md",
    "skills/model-resolution/SKILL.md",
    "skills/github-repo-setup/SKILL.md",
]
POLICY_FILES += sorted(str(p.relative_to(BASE)) for p in (BASE / "essentials").glob("*.md"))
FOUNDATION_POLICY_FILES = POLICY_FILES + [
    "docs/roadmap.md",
    "skills/reference-driven-development/references/contract.md",
    # Routing/capture skills that govern foundation-pack usage (not the pack leaves).
    "skills/awesome-guidelines/SKILL.md",
    "skills/evidence-router/SKILL.md",
    "skills/frontend-markup-practices/SKILL.md",
    "skills/leverage-capture/SKILL.md",
    "skills/project-bootstrap/SKILL.md",
    "skills/reference-driven-development/SKILL.md",
    "skills/skill-catalog/SKILL.md",
    "skills/writing-skills/SKILL.md",
]

fails: List[str] = []
warns: List[str] = []


def read(rel: str) -> Optional[str]:
    p = BASE / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def check_fail(cid: str, rel: str, line_no: int, detail: str) -> None:
    fails.append(f"[{cid}] {rel}:{line_no}: {detail}")


def forbid_phrase(cid: str, phrase: str, files=None) -> None:
    # files: sequence of policy paths, defaults to POLICY_FILES.
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
    """'prewalk' in global policy docs is forbidden; pi Fabric owns the term in fabric-native-execution."""
    skip = {"skills/fabric-native-execution/SKILL.md"}
    for rel in POLICY_FILES:
        if rel in skip:
            continue
        text = read(rel)
        if not text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"prewalk", line, re.I):
                check_fail("PREWALK-RESERVED", rel, i + 1, "'prewalk' belongs in pi host config/skills, not global policy")


def check_lifecycle_optional() -> None:
    """Entry flow is opt-in; ordinary work never requires lifecycle machinery."""
    for rel in ("README.md", "skills/project-bootstrap/SKILL.md"):
        text = read(rel) or ""
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"mandatory default", line, re.I):
                check_fail("LIFECYCLE-OPTIONAL", rel, i, "'mandatory default' loop language")
    require_phrase("LIFECYCLE-OPTIONAL", "README.md", "No lifecycle machinery")
    require_phrase("LIFECYCLE-OPTIONAL", "skills/project-bootstrap/SKILL.md", "No persistent files")


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


# Canonical MCP capability registry: every server a fresh clone can wire.
EXPECTED_MCP_SERVERS = {"codebase-memory", "context7", "deepwiki", "exa", "openviking", "mcp-steroid"}
MACHINE_LOCAL_PATHS = ("/home/", "/mnt/", "/Users/", "C:\\")


def check_mcp_portable() -> None:
    """Canonical registry is readable, complete, and portable: commands resolve
    via PATH, and no machine-local absolute path is frozen into it. Machine-local
    values ride in process env (exported by the shell profile), never here."""
    data = read("mcp/servers.json")
    try:
        servers = json.loads(data)["mcpServers"]
    except Exception as exc:
        fails.append(f"[MCP-REGISTRY] mcp/servers.json unreadable or missing mcpServers: {exc}")
        return
    missing = EXPECTED_MCP_SERVERS - set(servers)
    if missing:
        fails.append(f"[MCP-REGISTRY] mcp/servers.json missing canonical servers: {sorted(missing)}")
    for name, cfg in servers.items():
        for key in ("command", *cfg.get("args", [])):
            val = str(cfg.get("command") if key == "command" else key)
            if val.startswith("/") or any(marker in val for marker in MACHINE_LOCAL_PATHS):
                fails.append(f"[MCP-PORTABLE] servers.json: server {name!r} uses absolute path: {val}")
        for k, v in (cfg.get("env") or {}).items():
            if isinstance(v, str) and (v.startswith("/") or any(marker in v for marker in MACHINE_LOCAL_PATHS)):
                fails.append(
                    f"[MCP-PORTABLE] servers.json: {name}.env.{k} freezes a machine-local value: {v} "
                    f"(reference it by name or inherit from the process environment)")


def check_ut_gate_scoped() -> None:
    """universal-template validators are scoped to this repo, never universal."""
    require_phrase(
        "UT-GATE-SCOPED",
        "CONTRIBUTING.md",
        "not universal requirements for other projects",
    )


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
    """Essentials never promise automated mass ingestion of external repos."""
    for rel in ("essentials/README.md", "docs/roadmap.md"):
        text = read(rel)
        if text is None:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if "squeeze" in low or re.search(r"100%\s+(inspiration\s+)?ingestion", low) or "full squeeze" in low:
                check_fail("NO-MASS-INGESTION", rel, i, "mass-ingestion promise in policy docs")


def check_router_visibility() -> None:
    """*-router skills are cold references; they must stay hidden from startup metadata."""
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
        if not re.search(r"^disable-model-invocation:\s*true", text, re.M):
            check_fail(
                "ROUTER-VISIBILITY",
                rel,
                1,
                "router skills are cold references — set disable-model-invocation: true",
            )


def check_evidence_router_scope() -> None:
    """evidence-router routes EVIDENCE only: no provider/model selection content."""
    rel = "skills/evidence-router/SKILL.md"
    text = read(rel)
    if text is None:
        return
    banned = re.compile(r"veda\b|\bagy\b|codex|claude|opus|gemini|gpt-|deepseek|qwen", re.I)
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


def check_resolver_checkout_local() -> None:
    """resolve-model.py loads the CHECKED-OUT preference chain, not ~/.agents — proven from a temp checkout."""
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "scripts").mkdir()
        (root / "config").mkdir()
        shutil.copy(BASE / "scripts/resolve-model.py", root / "scripts/resolve-model.py")
        prof = (BASE / "config/model-profiles.yaml").read_text()
        prof = prof.replace(
            "  economy-worker:\n    prefer:\n",
            "  economy-worker:\n    prefer:\n      - pi:sentinel/checkout-probe-model\n", 1)
        (root / "config/model-profiles.yaml").write_text(prof)
        try:
            p = subprocess.run(
                ["python3", str(root / "scripts/resolve-model.py"), "--role", "MAIN", "--json"],
                capture_output=True, text=True, timeout=90, cwd=str(root))
            data = json.loads(p.stdout)
            if "pi:sentinel/checkout-probe-model" not in data.get("preference_chain", []):
                fails.append("[RESOLVER-CHECKOUT-LOCAL] resolve-model.py ignored the checkout-local preference file when run outside ~/.agents")
        except Exception as exc:
            fails.append(f"[RESOLVER-CHECKOUT-LOCAL] {type(exc).__name__}: {exc}")


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



def check_agents_safety_core() -> None:
    """AGENTS.md must retain the operational destructive-confirmation core."""
    require_phrase("AGENTS-SAFETY-CORE", "AGENTS.md", "Confirmation (quote the exact command")
    require_phrase("AGENTS-SAFETY-CORE", "AGENTS.md", "Never expose, invent, or commit credentials")
    require_phrase("AGENTS-SAFETY-CORE", "AGENTS.md", "history rewrites: `git reset --hard`, `git clean -fd`, force-push")
    require_phrase("AGENTS-SAFETY-CORE", "AGENTS.md", "bounded to the current repository")



def check_stale_agents_template() -> None:
    """The generated project AGENTS template must not re-infect projects with retired architecture."""
    rel = "templates/agents.md"
    text = read(rel)
    if text is None:
        fails.append("[STALE-AGENTS-TEMPLATE] templates/agents.md: file missing")
        return
    banned = re.compile(r"codegraphcontext|\.pi/essentials|\.pi/project\.md|Codebase Memory for graph orientation", re.I)
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail("STALE-AGENTS-TEMPLATE", rel, i, "retired architecture in the project AGENTS template")


def check_init_routing() -> None:
    """Project bootstrap routes evidence need-driven — never CodeMemory-first."""
    rel = "skills/project-bootstrap/SKILL.md"
    text = read(rel)
    if text is None:
        fails.append("[INIT-ROUTING] skills/project-bootstrap/SKILL.md: file missing")
        return
    if re.search(r"codebase memory first|search_graph on the covered project|run through the context layer first", text, re.I):
        check_fail("INIT-ROUTING", rel, 1, "bootstrap mandates a CodeMemory-first ritual instead of need-driven routing")
    flat = re.sub(r"\s+", " ", text)
    if "direct source first" not in flat and "evidence-router" not in flat:
        check_fail("INIT-ROUTING", rel, 1, "bootstrap must prefer direct source before optional capability maps")


def check_no_user_profile() -> None:
    """Project bootstrap/init must never create a user-profile artifact."""
    for rel in ("skills/project-bootstrap/SKILL.md", "AGENTS.md"):
        text = read(rel)
        if text is None:
            continue
        if re.search(r"\buser\.md\b", text):
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(r"\buser\.md\b", line):
                    check_fail("NO-USER-PROFILE", rel, i, "user-profile artifact is retired from project state")


def check_no_artifact_pack() -> None:
    """Bootstrap must not generate default host artifact packs."""
    rel = "skills/project-bootstrap/SKILL.md"
    text = read(rel)
    if text is None:
        return
    require_phrase("NO-ARTIFACT-PACK", rel, "host artifact packs")
    if re.search(r"\.pi/(project|tech-stack|roadmap|state|user)\.md.*by default", text, re.I):
        check_fail("NO-ARTIFACT-PACK", rel, 1, "name host artifact packs generically; pi paths are examples only")


def check_objective_drift() -> None:
    """Essentials never promise zero defects, universal code-taste metrics, or automatic per-session capture."""
    for rel in ("docs/roadmap.md", "essentials/operating-philosophy.md"):
        text = read(rel)
        if text is None:
            continue
        banned = re.compile(r"zero-?defect|convert aesthetic principles into deterministic AST metrics|mandatory skill capture|capture into skills after (a|every) session", re.I)
        for i, line in enumerate(text.splitlines(), 1):
            if banned.search(line):
                check_fail("OBJECTIVE-DRIFT", rel, i, "obsolete quality/capture objective resurfaced")


def check_foundation_first_class() -> None:
    """Foundations are durable leverage — not scheduled retirement or a no-new-foundations ban."""
    banned_phrases = (
        "no new foundations",
        "retired over time",
        "temporary cold prior-art",
        "foundation creation is frozen",
    )
    for phrase in banned_phrases:
        for rel in FOUNDATION_POLICY_FILES:
            text = read(rel)
            if not text:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if phrase.lower() in line.lower():
                    check_fail("FOUNDATION-FIRST-CLASS", rel, i, f"obsolete foundation policy: {phrase!r}")
    require_phrase(
        "FOUNDATION-FIRST-CLASS",
        "skills/reference-driven-development/references/contract.md",
        "References vs foundations",
    )
    require_phrase(
        "FOUNDATION-FIRST-CLASS",
        "README.md",
        "accumulated implementation foundations",
    )


AGENTS_WORKFLOW_PATTERNS = (
    (
        "procedural handbook section",
        re.compile(
            r"^#{1,6}\s+(?:mandatory\s+)?(?:workflow|execution phases?|phases?|"
            r"tool chain|router|decision matrix|scoring (?:engine|matrix))\s*$",
            re.I | re.M,
        ),
    ),
    (
        "fixed tool sequence",
        re.compile(
            r"\b(?:always|must|shall|required to)\s+(?:first\s+)?"
            r"(?:use|invoke|call|query|run)\b[^\n]{0,120}"
            r"\b(?:then|followed by|before)\b",
            re.I,
        ),
    ),
    (
        "mandatory router",
        re.compile(r"\broute\s+(?:every|all)\s+(?:task|request|change)\b", re.I),
    ),
    (
        "scoring system",
        re.compile(r"\bscore\s+(?:every|each|all)\s+(?:task|request|change)\b", re.I),
    ),
    (
        "unconditional delegation",
        re.compile(
            r"\b(?:always\s+delegate|delegate\s+(?:every|all)\s+"
            r"(?:task|request|change)|use\s+(?:an?\s+)?agents?\s+for\s+"
            r"(?:every|all)\s+(?:task|request|change))\b",
            re.I,
        ),
    ),
    (
        "unconditional research",
        re.compile(
            r"\b(?:always\s+research|research\s+(?:every|all)\s+"
            r"(?:task|request|change)|browse\s+the\s+web\s+for\s+"
            r"(?:every|all)\s+(?:task|request|change))\b",
            re.I,
        ),
    ),
)


def agents_workflow_violations(text: str) -> list[tuple[int, str]]:
    """Return workflow-handbook forms that violate constitutional autonomy."""
    violations = []
    for detail, pattern in AGENTS_WORKFLOW_PATTERNS:
        match = pattern.search(text)
        if match:
            violations.append((text.count("\n", 0, match.start()) + 1, detail))
    return violations


def check_agents_constitution() -> None:
    """Global AGENTS.md stays an outcome constitution, not a routing handbook."""
    rel = "AGENTS.md"
    text = read(rel)
    if text is None:
        fails.append("[AGENTS-CONSTITUTION] AGENTS.md: file missing")
        return
    for phrase in (
        "Optimize toward the Pareto frontier.",
        "Do not force a fixed tool sequence",
        "Keep this file a global engineering constitution, not a mandatory execution workflow.",
    ):
        require_phrase("AGENTS-CONSTITUTION", rel, phrase)
    banned = re.compile(
        r"Fovea|Steroid / JetBrains|foundation-pack/.*reusable architecture|"
        r"Evidence priority for non-trivial|Pi Fabric|fabric_exec|/fabric prewalk|"
        r"pi\.edit|pi\.write|pi\.bash|python3 scripts/|skill-validator\.py|"
        r"Entry skills|host wiring|~/.claude|~/.codex",
        re.I,
    )
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail(
                "AGENTS-CONSTITUTION",
                rel,
                i,
                "repo-specific or detailed routing content belongs elsewhere, not global AGENTS.md",
            )
    for line_no, detail in agents_workflow_violations(text):
        check_fail(
            "AGENTS-CONSTITUTION",
            rel,
            line_no,
            f"mandatory workflow form belongs in an owning capability: {detail}",
        )


def check_evidence_router_priority() -> None:
    """evidence-router owns the global evidence priority chain."""
    rel = "skills/evidence-router/SKILL.md"
    text = read(rel)
    if text is None:
        fails.append("[EVIDENCE-ROUTER-PRIORITY] skills/evidence-router/SKILL.md: file missing")
        return
    for phrase in ("Evidence priority", "no fixed tool chain", "foundation-pack/"):
        if phrase not in re.sub(r"\s+", " ", text):
            check_fail("EVIDENCE-ROUTER-PRIORITY", rel, 1, f"missing {phrase!r}")


def check_bootstrap_reference_inventory() -> None:
    """Project bootstrap must surface existing project-local reference assets."""
    rel = "skills/project-bootstrap/SKILL.md"
    text = read(rel)
    if text is None:
        fails.append("[BOOTSTRAP-REFERENCE-INVENTORY] skills/project-bootstrap/SKILL.md: file missing")
        return
    flat = re.sub(r"\s+", " ", text)
    for token in ("reference/", "reference/web/"):
        if token not in flat:
            check_fail("BOOTSTRAP-REFERENCE-INVENTORY", rel, 1, f"missing bounded inventory for {token!r}")
    require_phrase(
        "BOOTSTRAP-REFERENCE-INVENTORY",
        rel,
        "filesystem listing",
    )


def check_rdd_existing_references() -> None:
    """Reference-driven development activates when project-local references already exist."""
    rel = "skills/reference-driven-development/SKILL.md"
    text = read(rel)
    if text is None:
        fails.append("[RDD-EXISTING-REFERENCES] skills/reference-driven-development/SKILL.md: file missing")
        return
    flat = re.sub(r"\s+", " ", text)
    if "reference/web/" not in flat or "already exists" not in flat:
        check_fail(
            "RDD-EXISTING-REFERENCES",
            rel,
            1,
            "reference-driven-development must activate on existing project-local references",
        )


def check_rdd_retrieval_surface() -> None:
    """RDD description is the retrieval surface; it must mention existing project-local references."""
    rel = "skills/reference-driven-development/SKILL.md"
    text = read(rel)
    if text is None:
        fails.append("[RDD-RETRIEVAL-SURFACE] skills/reference-driven-development/SKILL.md: file missing")
        return
    spec = importlib.util.spec_from_file_location(
        "catalog_quality", str(Path(__file__).with_name("catalog-quality.py")))
    if spec is None or spec.loader is None:
        check_fail("RDD-RETRIEVAL-SURFACE", rel, 1, "catalog-quality unavailable")
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fm = mod.parse_frontmatter(text)
    desc = re.sub(r"\s+", " ", str(fm.get("description", "")))
    if "reference/web/" not in desc:
        check_fail(
            "RDD-RETRIEVAL-SURFACE",
            rel,
            1,
            "RDD description must mention reference/web/ for retrieval",
        )
    if "reference/<repo>/" not in desc and "reference/<repo>" not in desc:
        check_fail(
            "RDD-RETRIEVAL-SURFACE",
            rel,
            1,
            "RDD description must mention reference/<repo>/ for retrieval",
        )
    if "already exists" not in desc:
        check_fail(
            "RDD-RETRIEVAL-SURFACE",
            rel,
            1,
            "RDD description must state existing references activate the skill",
        )


FOUNDATION_FIRST_RE = re.compile(
    r"foundation-pack/`?\s*first|"
    r"(?:follow|load|use|consult)\s+(?:stack\s+capsules\s+in\s+)?[`']?foundation-pack[`']?\s+first|"
    r"[`']foundation-pack/[`']?\s+before\s+(?:current\s+)?project",
    re.I,
)


def check_foundation_priority_inversion(*, base: Path | None = None) -> None:
    """Active skills must not instruct generic foundation-pack before project/reference evidence."""
    root = base or BASE
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        rel = str(skill_md.relative_to(root))
        for i, line in enumerate(skill_md.read_text(encoding="utf-8").splitlines(), 1):
            if FOUNDATION_FIRST_RE.search(line):
                check_fail(
                    "FOUNDATION-PRIORITY",
                    rel,
                    i,
                    "generic foundation-pack before project/reference (see evidence-router priority)",
                )


def check_foundation_not_in_startup_catalog() -> None:
    """Foundations stay outside generated skill catalog entries."""
    gen = read("docs/skill-catalog.md")
    if gen is None:
        return
    if re.search(r"\| \[`[^`]+-foundation`\]", gen):
        check_fail(
            "FOUNDATION-NOT-STARTUP",
            "docs/skill-catalog.md",
            1,
            "foundations must not appear as active catalog skills",
        )


# Real callers for reachability: another SKILL.md or its references, top-level
# policy, runtime scripts, and CI config. Generated views (docs/skill-catalog.md),
# inventories, roadmap, and templates are NOT
# callers — a generated index must never make a dead skill look reachable.
REACHABILITY_CALLER_PARTS = ("AGENTS.md", "README.md", "CONTRIBUTING.md")
# Catalog machinery that enumerates skill names by design (classification sets,
# visibility policy, discovery, migration patterns). Every internal skill name
# appears there, so counting it as a caller makes the gate self-satisfying.
REACHABILITY_ENUMERATION_SCRIPTS = {
    "catalog-quality.py", "skill-validator.py", "skill-catalog.py",
    "policy-consistency.py", "legacy-skill-report.py",
}


def _reachability_corpus(base: Path) -> List[Tuple[str, Path]]:
    corpus: List[Tuple[str, Path]] = []
    skills = base / "skills"
    if skills.is_dir():
        for d in sorted(skills.iterdir()):
            if not d.is_dir():
                continue
            sm = d / "SKILL.md"
            if sm.is_file():
                corpus.append((d.name, sm))
            refs = d / "references"
            if refs.is_dir():
                corpus.extend((d.name, f) for f in sorted(refs.glob("*.md")))
    for name in REACHABILITY_CALLER_PARTS:
        p = base / name
        if p.is_file():
            corpus.append(("", p))
    scripts = base / "scripts"
    if scripts.is_dir():
        corpus.extend(("", f) for f in sorted(scripts.glob("*.py"))
                      if f.name not in REACHABILITY_ENUMERATION_SCRIPTS)
    gh = base / ".github"
    if gh.is_dir():
        corpus.extend(("", f) for f in sorted(gh.rglob("*")) if f.is_file())
    return corpus


def _load_internal_skills() -> Set[str]:
    """One classification source: catalog-quality.py owns INTERNAL_SKILLS."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "catalog_quality_pc", str(Path(__file__).with_name("catalog-quality.py")))
    if spec is None or spec.loader is None:
        return set()
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return set(getattr(mod, "INTERNAL_SKILLS", set()))
    except Exception:  # noqa: BLE001
        return set()


def check_hidden_reachability(base: Path = BASE, internal=None) -> List[str]:
    """Internal hidden skills need a real caller; cold ones are reachable via search.

    A hidden skill (disable-model-invocation: true) counts as reachable when any
    of these hold:
    - x-manual-only: true (explicitly designated manual-only)
    - it classifies as cold (hidden, not internal) — skill-catalog search is its
      discovery path, so it needs no route
    - otherwise (internal): some real caller names it. Generated catalogs,
      inventory docs, and other derived views are excluded from the caller scan.
    """
    if internal is None:
        internal = _load_internal_skills()
    skills_dir = base / "skills"
    if not skills_dir.is_dir():
        return []
    corpus = _reachability_corpus(base)
    dead: List[str] = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        skill_file = d / "SKILL.md"
        if not skill_file.is_file():
            continue
        try:
            text = skill_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if not re.search(r"^disable-model-invocation:\s*true", text, re.M):
            continue
        if re.search(r"^x-manual-only:\s*true", text, re.M):
            continue
        if d.name not in internal:
            continue  # cold: searchable through skill-catalog
        needle = d.name
        reachable = any(owner != needle and needle in f.read_text(encoding="utf-8", errors="ignore")
                        for owner, f in corpus)
        if not reachable:
            dead.append(d.name)
            if base == BASE:
                check_fail("HIDDEN-REACHABILITY", f"skills/{needle}/SKILL.md", 1,
                           "internal hidden skill has no incoming reference from a real caller "
                           "(skill docs, AGENTS/APPEND, scripts, CI) — add a route, reclassify it "
                           "cold, or make it visible")
    return dead


def check_readme_skill_refs() -> None:
    """Every skills/<name> referenced from README.md must exist; retired names must not return."""
    readme = BASE / "README.md"
    if not readme.is_file():
        fails.append("[README-SKILL-REFS] README.md: file missing")
        return
    text = readme.read_text(encoding="utf-8")
    for m in re.finditer(r"skills/([a-z0-9-]+)", text):
        name = m.group(1)
        if not (BASE / f"skills/{name}/SKILL.md").is_file():
            check_fail("README-SKILL-REFS", "README.md", 1, f"stale skill reference: skills/{name}")
    for stale in ("workflow-lifecycle", "five-source", "Codebase Memory observation"):
        if stale.lower() in text.lower():
            check_fail("README-SKILL-REFS", "README.md", 1, f"retired concept present: {stale!r}")


def check_github_ownership() -> None:
    """GitHub skill ownership stays exclusive (no duplicated canonical claims)."""
    push_pr = BASE / "skills/push-pr/SKILL.md"
    repo_setup = BASE / "skills/github-repo-setup/SKILL.md"
    git_wf = BASE / "skills/git-workflow-and-versioning/SKILL.md"
    ghe = BASE / "skills/github-actions-engineering/SKILL.md"
    if push_pr.is_file() and re.search(r"ruleset", push_pr.read_text(encoding="utf-8"), re.I):
        check_fail("GITHUB-OWNERSHIP", "skills/push-pr/SKILL.md", 1, "PR lifecycle skill must not claim ruleset governance")
    if repo_setup.is_file() and "gh pr create" in repo_setup.read_text(encoding="utf-8"):
        check_fail("GITHUB-OWNERSHIP", "skills/github-repo-setup/SKILL.md", 1, "repository setup must not own PR creation (push-pr does)")
    if git_wf.is_file() and re.search(r"github-actions-engineering\s*$", git_wf.read_text(encoding="utf-8"), re.M):
        check_fail("GITHUB-OWNERSHIP", "skills/git-workflow-and-versioning/SKILL.md", 1, "versioning skill must not claim Actions ownership")
    if ghe.is_file() and re.search(r"gh api .*rulesets", ghe.read_text(encoding="utf-8")):
        check_fail("GITHUB-OWNERSHIP", "skills/github-actions-engineering/SKILL.md", 1, "Actions skill must not configure remote rulesets (github-repo-setup does)")



def check_pr_ownership() -> None:
    """github-repo-setup must not claim general PR-creation ownership — push-pr owns the PR lifecycle."""
    rel = "skills/github-repo-setup/SKILL.md"
    text = read(rel)
    if text is None:
        return
    if re.search(r"evidence-based PR", text, re.I):
        check_fail("PR-OWNERSHIP", rel, 1, "general PR creation belongs to push-pr, not repo-setup")



def check_web_reference_split() -> None:
    """web-reference owns site capture; the contract recognizes web references; rdd stays crawler-free."""
    contract_text = read("skills/reference-driven-development/references/contract.md") or ""
    if "web reference" not in contract_text.lower():
        fails.append("[WEBREF-SPLIT] skills/reference-driven-development/references/contract.md: required phrase missing: 'web reference'")
    rel = "skills/web-reference/SKILL.md"
    text = read(rel)
    if text is None:
        fails.append("[WEBREF-SPLIT] skills/web-reference/SKILL.md: file missing")
        return
    flat = re.sub(r"\s+", " ", text)
    for token in ("ADOPT", "ADAPT", "OMIT"):
        if token not in flat:
            check_fail("WEBREF-SPLIT", rel, 1, "web-reference must carry the ADOPT/ADAPT/OMIT model")
    if "implementation and acceptance authority" not in flat:
        check_fail("WEBREF-SPLIT", rel, 1, "web-reference must defer acceptance to the current project")
    rdd_text = (read("skills/reference-driven-development/SKILL.md") or "").lower()
    for token in ("browsertrix", "browser-harness", "wacz"):
        if token in rdd_text:
            check_fail("WEBREF-SPLIT", "skills/reference-driven-development/SKILL.md", 1, f"crawler mechanics in reference-driven-development: {token}")


QUALITY_COMMAND_RE = re.compile(r"python3 scripts/([a-z0-9-]+\.py)([^\n|#]*)")


def quality_gate_commands(text: str) -> set[tuple[str, str]]:
    """Return script and mode pairs from a repository quality command block."""
    commands = set()
    for match in QUALITY_COMMAND_RE.finditer(text):
        args = match.group(2).split()
        mode = next((arg for arg in ("--check-repo", "--selftest") if arg in args), "")
        commands.add((match.group(1), mode))
    return commands


def contributing_gate_commands(text: str) -> set[tuple[str, str]]:
    """Read the canonical fenced gate block from CONTRIBUTING.md."""
    match = re.search(r"## Before pushing.*?```bash\n(.*?)```", text, re.S)
    return quality_gate_commands(match.group(1)) if match else set()


def quality_gate_parity_errors(contrib: str, workflows: dict[str, str]) -> list[str]:
    """Report canonical repository gates missing from a workflow."""
    expected = contributing_gate_commands(contrib)
    if not expected:
        return ["CONTRIBUTING.md canonical gate block is missing or empty"]
    errors = []
    for rel, text in workflows.items():
        missing = sorted(expected - quality_gate_commands(text))
        for script, mode in missing:
            command = f"{script} {mode}".rstrip()
            errors.append(f"{rel} missing canonical gate: {command}")
    return errors


def release_workflow_errors(text: str) -> list[str]:
    """Report release boundaries that protect verification and publishing."""
    errors = []
    required = (
        ("permissions:\n  contents: read", "top-level contents permission must be read-only"),
        ("fetch-depth: 2", "checkout must fetch the tagged commit parent"),
        ('CHECK_RANGE="$GITHUB_SHA^..$GITHUB_SHA"', "conventional range must use the tagged commit"),
        ('git diff --check "$GITHUB_SHA^" "$GITHUB_SHA"', "whitespace check must inspect the tagged commit"),
        ("needs: verify", "publish must depend on verification"),
        ("permissions:\n      contents: write", "only the publish job may write releases"),
    )
    for phrase, detail in required:
        if phrase not in text:
            errors.append(detail)
    if any(line.strip() == "git diff --check" for line in text.splitlines()):
        errors.append("bare git diff --check only inspects the clean worktree")
    if re.search(r"^permissions:\n  contents: write$", text, re.M):
        errors.append("top-level contents write exposes the verification job")
    return errors


def check_quality_gate_parity() -> None:
    """PR and release workflows run the canonical CONTRIBUTING gate suite."""
    contrib = read("CONTRIBUTING.md") or ""
    workflow_paths = (".github/workflows/pr-quality.yml", ".github/workflows/release.yml")
    workflows = {rel: read(rel) or "" for rel in workflow_paths}
    for detail in quality_gate_parity_errors(contrib, workflows):
        check_fail("QUALITY-GATE-PARITY", "CONTRIBUTING.md", 1, detail)
    for detail in release_workflow_errors(workflows[".github/workflows/release.yml"]):
        check_fail("QUALITY-GATE-PARITY", ".github/workflows/release.yml", 1, detail)


def check_gate_documentation() -> None:
    """CONTRIBUTING.md documents the required gate scripts for this repository.
    README/AGENTS carry no volatile template counts or retired artifacts;
    catalog-quality.py checks the actual templates/ and essentials/ directories."""
    contrib = read("CONTRIBUTING.md") or ""
    for needle in ("skill-validator.py", "repo-hygiene.py", "catalog-quality.py"):
        if needle not in contrib:
            fails.append(f"[GATE-DOCS] CONTRIBUTING.md must document the required gate script: {needle}")
    for rel in ("README.md", "AGENTS.md"):
        text = read(rel) or ""
        if re.search(r"\d+\s+CLI-neutral", text):
            fails.append(f"[GATE-DOCS] {rel} must not state a template count; templates/ is authoritative")
        for retired in ("project.md", "state.md", "tech-stack.md", "user.md"):
            if retired in text:
                fails.append(f"[GATE-DOCS] {rel} lists retired template as current: {retired}")


def selftest() -> int:
    """Golden test: a generated catalog must not make a dead internal skill
    look reachable; a real caller must."""
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        skills = base / "skills"
        (skills / "alpha").mkdir(parents=True)
        (skills / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: Use when testing.\n---\n# Alpha\n", encoding="utf-8")
        (skills / "gamma").mkdir()
        (skills / "gamma" / "SKILL.md").write_text(
            "---\nname: gamma\ndescription: Use when testing.\n"
            "disable-model-invocation: true\n---\n# Gamma (cold, searchable)\n", encoding="utf-8")
        (skills / "delta").mkdir()
        (skills / "delta" / "SKILL.md").write_text(
            "---\nname: delta\ndescription: Use when testing.\n"
            "disable-model-invocation: true\n---\n# Delta (internal)\n", encoding="utf-8")
        # The generated catalog names delta — this must NOT make it reachable.
        (base / "docs").mkdir()
        (base / "docs" / "skill-catalog.md").write_text(
            "# Catalog\n- delta\n", encoding="utf-8")
        internal = {"delta"}
        dead = check_hidden_reachability(base=base, internal=internal)
        if dead == ["delta"]:
            print("PASS catalog-only reference leaves internal skill unreachable")
        else:
            print(f"FAIL expected ['delta'] unreachable, got {dead}")
            ok = False
        # A real caller (another SKILL.md) makes it reachable.
        (skills / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: Use when testing.\n---\n"
            "# Alpha\nRoute to `delta` for this.\n", encoding="utf-8")
        dead = check_hidden_reachability(base=base, internal=internal)
        if not dead:
            print("PASS real caller makes internal skill reachable")
        else:
            print(f"FAIL expected [] unreachable, got {dead}")
            ok = False
        # Cold hidden skills never need a route.
        dead = check_hidden_reachability(base=base, internal=set())
        if not dead:
            print("PASS cold hidden skills need no route")
        else:
            print(f"FAIL expected [] unreachable, got {dead}")
            ok = False
    # Production classification path: load INTERNAL_SKILLS from
    # catalog-quality.py exactly as the gate does, then prove a real internal
    # skill flips unreachable -> reachable when its only caller appears. This
    # catches the corpus regaining a self-satisfying source (classification or
    # generated-discovery scripts must stay excluded).
    internal = _load_internal_skills()
    if not internal:
        print("FAIL production INTERNAL_SKILLS failed to load")
        return 1
    probe = next(name for name in sorted(internal)
                 if (BASE / "skills" / name / "SKILL.md").is_file())
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "skills" / probe).mkdir(parents=True)
        (base / "skills" / probe / "SKILL.md").write_text(
            "---\nname: " + probe + "\ndescription: Use when testing.\n"
            "disable-model-invocation: true\n---\n# probe\n", encoding="utf-8")
        (base / "docs").mkdir()
        (base / "docs" / "skill-catalog.md").write_text(
            "# Catalog\n- " + probe + "\n", encoding="utf-8")
        dead = check_hidden_reachability(base=base, internal=internal)
        if dead != [probe]:
            print(f"FAIL production internal skill {probe} should be unreachable, got {dead}")
            ok = False
        else:
            print("PASS production classification: unreachable without a real caller")
        # A second skill names the probe: a real caller flips it reachable.
        # (A self-reference in the probe's own SKILL.md never counts — the
        # corpus excludes the skill's own directory.)
        (base / "skills" / "caller").mkdir()
        (base / "skills" / "caller" / "SKILL.md").write_text(
            "---\nname: caller\ndescription: Use when testing.\n---\n"
            "# caller\nRoute to " + probe + " during the workflow.\n", encoding="utf-8")
        dead = check_hidden_reachability(base=base, internal=internal)
        if dead:
            print(f"FAIL production internal skill {probe} should be reachable, got {dead}")
            ok = False
        else:
            print("PASS production classification: reachable with a real caller")
    required_foundation_policy = {
        "skills/skill-catalog/SKILL.md",
        "skills/writing-skills/SKILL.md",
    }
    if not required_foundation_policy.issubset(set(FOUNDATION_POLICY_FILES)):
        print(f"FAIL FOUNDATION_POLICY_FILES missing {required_foundation_policy - set(FOUNDATION_POLICY_FILES)}")
        ok = False
    else:
        print("PASS foundation policy scope includes routing skills")
    # Foundation-priority regression: bad skill fails, good skill passes.
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "skills" / "priority-probe-bad").mkdir(parents=True)
        (base / "skills" / "priority-probe-good").mkdir(parents=True)
        (base / "skills" / "priority-probe-bad" / "SKILL.md").write_text(
            "---\nname: priority-probe-bad\ndescription: Use when testing.\n---\n"
            "follow stack capsules in `foundation-pack/` first\n",
            encoding="utf-8",
        )
        (base / "skills" / "priority-probe-good" / "SKILL.md").write_text(
            "---\nname: priority-probe-good\ndescription: Use when testing.\n---\n"
            "after current project code, consult applicable stack capsules in `foundation-pack/`.\n",
            encoding="utf-8",
        )
        fails_before = len(fails)
        check_foundation_priority_inversion(base=base)
        new_fails = [f for f in fails[fails_before:] if "priority-probe-bad" in f]
        if len(new_fails) != 1:
            print(f"FAIL foundation-priority should flag bad probe once, got {new_fails}")
            ok = False
        else:
            print("PASS foundation-priority catches generic foundation-first instruction")
        if any("priority-probe-good" in f for f in fails[fails_before:]):
            print("FAIL foundation-priority should not flag corrected ordering")
            ok = False
        fails[:] = fails[:fails_before]
    agents_good = """# Constitution
Use tools that materially improve confidence. Use agents when delegation helps.
Research load-bearing facts when the expected confidence gain justifies the cost.
"""
    agents_bad = {
        "mandatory phases": "## Mandatory workflow\nPhase 1: inspect\nPhase 2: implement\n",
        "fixed tool chain": "Always use Context7, then Exa before editing.\n",
        "router": "Route every task through the execution router.\n",
        "scoring matrix": "## Scoring matrix\nScore every change from 1 to 5.\n",
        "delegation": "Always delegate every task to an agent.\n",
        "research": "Research every task before editing.\n",
    }
    if agents_workflow_violations(agents_good):
        print("FAIL outcome-oriented AGENTS guidance was classified as a workflow")
        ok = False
    else:
        print("PASS outcome-oriented AGENTS guidance stays valid")
    for name, fixture in agents_bad.items():
        if agents_workflow_violations(fixture):
            print(f"PASS AGENTS constitution rejects {name}")
        else:
            print(f"FAIL AGENTS constitution missed {name}")
            ok = False
    gate_contrib = """## Before pushing
```bash
python3 scripts/alpha.py --selftest
python3 scripts/alpha.py
python3 scripts/beta.py
```
"""
    gate_good = """python3 scripts/alpha.py --selftest
python3 scripts/alpha.py
python3 scripts/beta.py
"""
    gate_missing = """python3 scripts/alpha.py
python3 scripts/beta.py
"""
    if quality_gate_parity_errors(gate_contrib, {"good.yml": gate_good}):
        print("FAIL complete quality workflow rejected")
        ok = False
    else:
        print("PASS quality parity accepts the complete canonical suite")
    missing_errors = quality_gate_parity_errors(gate_contrib, {"missing.yml": gate_missing})
    if any("alpha.py --selftest" in error for error in missing_errors):
        print("PASS quality parity catches a missing gate mode")
    else:
        print(f"FAIL quality parity missed a gate mode: {missing_errors}")
        ok = False
    release_good = """permissions:
  contents: read
fetch-depth: 2
CHECK_RANGE="$GITHUB_SHA^..$GITHUB_SHA"
git diff --check "$GITHUB_SHA^" "$GITHUB_SHA"
needs: verify
    permissions:
      contents: write
"""
    release_bad = """permissions:
  contents: write
git diff --check
"""
    if release_workflow_errors(release_good):
        print("FAIL safe release workflow fixture rejected")
        ok = False
    else:
        print("PASS release workflow accepts split privileges and commit ranges")
    bad_release_errors = release_workflow_errors(release_bad)
    if "bare git diff --check only inspects the clean worktree" in bad_release_errors and \
            "top-level contents write exposes the verification job" in bad_release_errors:
        print("PASS release workflow catches unsafe privilege and range boundaries")
    else:
        print(f"FAIL release workflow missed unsafe boundaries: {bad_release_errors}")
        ok = False
    print("policy-consistency selftest: PASS" if ok else "policy-consistency selftest: FAIL")
    return 0 if ok else 1


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
    ("RESOLVER-CHECKOUT-LOCAL", check_resolver_checkout_local),
    ("RUNTIME-JSON", check_runtime_json),
    ("ROUTER-REFS-RESOLVE", check_router_refs_resolve),
    ("AGENTS-SAFETY-CORE", check_agents_safety_core),
    ("STALE-AGENTS-TEMPLATE", check_stale_agents_template),
    ("INIT-ROUTING", check_init_routing),
    ("NO-USER-PROFILE", check_no_user_profile),
    ("NO-ARTIFACT-PACK", check_no_artifact_pack),
    ("OBJECTIVE-DRIFT", check_objective_drift),
    ("FOUNDATION-FIRST-CLASS", check_foundation_first_class),
    ("AGENTS-CONSTITUTION", check_agents_constitution),
    ("EVIDENCE-ROUTER-PRIORITY", check_evidence_router_priority),
    ("BOOTSTRAP-REFERENCE-INVENTORY", check_bootstrap_reference_inventory),
    ("RDD-EXISTING-REFERENCES", check_rdd_existing_references),
    ("RDD-RETRIEVAL-SURFACE", check_rdd_retrieval_surface),
    ("FOUNDATION-PRIORITY", check_foundation_priority_inversion),
    ("FOUNDATION-NOT-STARTUP", check_foundation_not_in_startup_catalog),
    ("HIDDEN-REACHABILITY", check_hidden_reachability),
    ("PR-OWNERSHIP", check_pr_ownership),
    ("README-SKILL-REFS", check_readme_skill_refs),
    ("GITHUB-OWNERSHIP", check_github_ownership),
    ("WEBREF-SPLIT", check_web_reference_split),
    ("QUALITY-GATE-PARITY", check_quality_gate_parity),
    ("GATE-DOCS", check_gate_documentation),
]


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
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
