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

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

BASE = Path(__file__).resolve().parents[1]

# essentials/*.md is policy as a set (globbed below) — new essentials docs are covered automatically.
POLICY_FILES = [
    "APPEND_SYSTEM.md",
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
    """Entry flow is opt-in; ordinary work never requires lifecycle machinery."""
    for rel in ("AGENTS.md", "README.md"):
        text = read(rel) or ""
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r"mandatory default", line, re.I):
                check_fail("LIFECYCLE-OPTIONAL", rel, i, "'mandatory default' loop language")
    require_phrase("LIFECYCLE-OPTIONAL", "AGENTS.md", "No lifecycle machinery is required for ordinary work")
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



def check_append_no_api_recipes() -> None:
    """APPEND_SYSTEM.md carries invariants only — no GitHub API/GraphQL recipes."""
    text = read("APPEND_SYSTEM.md")
    if text is None:
        fails.append("[APPEND-NO-API-RECIPES] APPEND_SYSTEM.md: file missing")
        return
    banned = re.compile(r"resolveReviewThread|api\.github\.com|in_reply_to|graphql|/repos/", re.I)
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail("APPEND-NO-API-RECIPES", "APPEND_SYSTEM.md", i, "GitHub API recipe belongs in the GitHub skill, not APPEND")


def check_append_no_model_slugs() -> None:
    """APPEND_SYSTEM.md never names model/provider routing specifics."""
    text = read("APPEND_SYSTEM.md")
    if text is None:
        return
    banned = re.compile(r"\b(agy|veda|claude|codex|copilot|deepseek|qwen|pi/|gemini)\b", re.I)
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail("APPEND-NO-MODEL-SLUGS", "APPEND_SYSTEM.md", i, "model/provider specifics belong in routing skills, not APPEND")


def check_append_no_commitlint_mandate() -> None:
    """APPEND never mandates a specific commitlint standard — convention is discovered per repository."""
    forbid_phrase("APPEND-NO-COMMITLINT-MANDATE", "commitlint standards", files=["APPEND_SYSTEM.md"])


def check_append_no_tool_coupling() -> None:
    """APPEND invariants are tool-neutral — never coupled to a tool literally named 'read'."""
    text = read("APPEND_SYSTEM.md")
    if text is None:
        return
    banned = re.compile(r"\bread tool\b|\bthe read tool\b", re.I)
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail("APPEND-NO-TOOL-COUPLING", "APPEND_SYSTEM.md", i, "artifact inspection must stay tool-neutral")


def check_append_compact() -> None:
    """APPEND stays a small execution constitution (~13 invariants), not a second AGENTS."""
    text = read("APPEND_SYSTEM.md")
    if text is None:
        return
    nonempty = sum(1 for line in text.splitlines() if line.strip())
    if nonempty > 60:
        check_fail("APPEND-COMPACT", "APPEND_SYSTEM.md", 1, f"{nonempty} non-empty lines — APPEND must stay under 60; move detail to AGENTS/skills/gates")


def check_append_bounded_search() -> None:
    """APPEND's filesystem rule must allow repository-root traversal while bounding discovery."""
    require_phrase("APPEND-BOUNDED-SEARCH", "APPEND_SYSTEM.md", "repository/workspace")
    require_phrase("APPEND-BOUNDED-SEARCH", "APPEND_SYSTEM.md", "repo root")


def check_agents_safety_core() -> None:
    """AGENTS.md must retain the operational destructive-confirmation core — hosts load AGENTS, not APPEND."""
    require_phrase("AGENTS-SAFETY-CORE", "AGENTS.md", "Confirmation (quote the exact command")
    require_phrase("AGENTS-SAFETY-CORE", "AGENTS.md", "Never expose, invent, or commit credentials")
    require_phrase("AGENTS-SAFETY-CORE", "AGENTS.md", "history rewrites: `git reset --hard`, `git clean -fd`, force-push")



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
    if "evidence-router" not in flat:
        check_fail("INIT-ROUTING", rel, 1, "bootstrap must reference need-driven evidence routing")


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
    """Bootstrap must not generate the .pi artifact pack (project/tech-stack/roadmap/state/user)."""
    rel = "skills/project-bootstrap/SKILL.md"
    text = read(rel)
    if text is None:
        return
    banned = re.compile(r"\.pi/(project|tech-stack|roadmap|state|user)\.md", re.I)
    for i, line in enumerate(text.splitlines(), 1):
        if banned.search(line):
            check_fail("NO-ARTIFACT-PACK", rel, i, "default .pi artifact pack is retired; persistent context is selective")


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


# Real callers for reachability: another SKILL.md or its references, top-level
# policy, runtime scripts, and CI config. Generated views (docs/skill-catalog.md),
# inventories, roadmap, and templates are NOT
# callers — a generated index must never make a dead skill look reachable.
REACHABILITY_CALLER_PARTS = ("AGENTS.md", "APPEND_SYSTEM.md", "README.md", "CONTRIBUTING.md")
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
    contract_text = read("references/reference-contract.md") or ""
    if "web reference" not in contract_text.lower():
        fails.append("[WEBREF-SPLIT] references/reference-contract.md: required phrase missing: 'web reference'")
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


def check_gate_documentation() -> None:
    """Absorbed from catalog-integrity.py (deleted): AGENTS.md documents the
    required gate scripts, and README/AGENTS carry no volatile inventory counts.
    The canonical template inventory (references/templates-inventory.md) is the
    only place that enumerates templates; counts there are machine-checked
    against disk by catalog-quality.py."""
    agents = read("AGENTS.md") or ""
    for needle in ("skill-validator.py", "repo-hygiene.py", "catalog-quality.py"):
        if needle not in agents:
            fails.append(f"[GATE-DOCS] AGENTS.md must document the required gate script: {needle}")
    for rel in ("README.md", "AGENTS.md"):
        text = read(rel) or ""
        if re.search(r"\d+\s+CLI-neutral", text):
            fails.append(f"[GATE-DOCS] {rel} states a template count; point at references/templates-inventory.md instead")
        if "references/templates-inventory.md" not in text and rel == "README.md":
            fails.append("[GATE-DOCS] README.md must point at references/templates-inventory.md as the canonical template inventory")
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
    ("APPEND-NO-API-RECIPES", check_append_no_api_recipes),
    ("APPEND-NO-MODEL-SLUGS", check_append_no_model_slugs),
    ("APPEND-NO-COMMITLINT-MANDATE", check_append_no_commitlint_mandate),
    ("APPEND-NO-TOOL-COUPLING", check_append_no_tool_coupling),
    ("APPEND-COMPACT", check_append_compact),
    ("APPEND-BOUNDED-SEARCH", check_append_bounded_search),
    ("AGENTS-SAFETY-CORE", check_agents_safety_core),
    ("STALE-AGENTS-TEMPLATE", check_stale_agents_template),
    ("INIT-ROUTING", check_init_routing),
    ("NO-USER-PROFILE", check_no_user_profile),
    ("NO-ARTIFACT-PACK", check_no_artifact_pack),
    ("OBJECTIVE-DRIFT", check_objective_drift),
    ("HIDDEN-REACHABILITY", check_hidden_reachability),
    ("PR-OWNERSHIP", check_pr_ownership),
    ("README-SKILL-REFS", check_readme_skill_refs),
    ("GITHUB-OWNERSHIP", check_github_ownership),
    ("WEBREF-SPLIT", check_web_reference_split),
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
