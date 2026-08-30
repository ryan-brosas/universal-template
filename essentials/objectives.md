# Essentials Objectives: Strategic & Tactical Implementation Goals

A concrete, actionable set of objectives derived directly from the four pillars
and test methodology of our operating philosophy. These objectives drive our
roadmap, skill development, testing harness, automation pipelines, and cron marathons.

---

## 🎯 Master Objective Summary

| Pillar / Methodology | Primary Strategic Objective | Target Milestone |
| :--- | :--- | :--- |
| **Pillar 1: Ground Truth** | 100% Inspiration Ingestion into per-repo foundation leaves (`skills/*-foundation`) via Two-Pass Learning | Full squeeze of all 73 inspo repos |
| **Pillar 2: Steer Outcomes** | Frictionless Conclusive PR Loop with Mechanical Gate Boundaries | Sub-30s CI checks, zero behavioral prompt bloat |
| **Pillar 3: Stack Leverage** | Automated Post-Session Skill Capture & Tripled-Layer Viking Memory | Autonomous `/learn` workflow and OpenViking sync |
| **Pillar 4: Mechanical Quality** | Universal + Language-Specific Quality Gates with Unbypassable Walls | Zero-defect automated gating across all projects |
| **Test Methodology** | Catch-First Verification Standard (Un-fixed RED $\to$ Fixed GREEN) | Mandatory pre-fix failure proofs on all bugfixes |

---

## 🏛️ Pillar 1 Objectives: Ground Truth & Guiding Small Models

> *"A small model lacks knowledge, not capacity. Give it ground truth to work from."*

### Tactical Objectives:
- [ ] **Objective 1.1 — Reference-Driven Prior Art (replaces mass ingestion):**
  - Useful external repositories become project-local `reference/<repo>/` checkouts — read source/tests, adopt/adapt/omit. Repo → foundation mining is **frozen** while this path is validated.
  - Deliberate foundation exceptions only: a named recurring porting question that source alone does not answer (`foundations-workflow`, one repo at a time).
  - Existing `*-foundation` leaves are preserved pending measured triage (keep / shrink / retire per `code-foundations`).
- [ ] **Objective 1.2 — 100% `<!-- capsule-v2 -->` Migration:**
  - Audit all references across every emergent foundation leaf (the flat `skills/*-foundation` layout) and ensure 100% adherence to the capsule-v2 contract (Source/Question, HEAD line numbers, Signature, Data Shape, decisive source, Flow, Invariant, direct test Probe, Retrieve query, Verdict).
  - Eliminate all remaining legacy capsule-v1 markdown files.
- [ ] **Objective 1.3 — Automated Code Graph Context Discovery:**
  - Standardize discovery routines so that before planning or editing, agents query the nearest sufficient source — direct code, Fovea (active-project structure), or Codebase Memory (cross-repo prior art) — instead of drafting from blank context. One primary route per question; escalate only on a named gap.

---

## 🎯 Pillar 2 Objectives: Steer Outcomes, Not Behavior

> *"Don't over-restrict the agent with scope discipline. Steer outcomes, not behavior."*

### Tactical Objectives:
- [ ] **Objective 2.1 — System Prompt & AGENTS.md De-Cluttering:**
  - Continuously audit `AGENTS.md`, `.pi/templates/agents.md`, and all `.pi/prompts/*.md` templates.
  - Strip out any restrictive behavioral rules ("simplest implementation", "grow in layers", "avoid abstraction").
  - Replace them with clear outcome contracts, binary pass/fail conditions, and mechanical validator commands.
- [ ] **Objective 2.2 — Ultra-Fast Conclusive PR Loop:**
  - Maintain sub-30s execution times on all GitHub Actions workflows (`quality-gate`, `check-integrity`, `dead-code`, `repo-hygiene`, `pr-title`).
  - Provide machine-readable annotations and auto-fix triggers on all pull requests.
- [ ] **Objective 2.3 — Quantitative Code Taste Enforcement:**
  - Replace vague "clean code" instructions with deterministic AST metrics:
    - Enforce maximum cyclomatic complexity thresholds via linters.
    - Ban single-caller utility wrappers and restating comments via AST rules.
    - Require strict type validation (`any` ban) across all TypeScript/Python assets.

---

## 💎 Pillar 3 Objectives: Stack Your Leverage (Code is Your Asset)

> *"Code from scratch is cheap; code you hold is valuable."*

### Tactical Objectives:
- [ ] **Objective 3.1 — Post-Session Skill Harvest With A Promotion Threshold:**
  - Implement a skill-harvesting prompt workflow (`/learn` or post-session hook) that extracts *recurring* edge cases, platform quirks, and verified recovery patterns into skill drafts. One-off details already recoverable from source stay in code, not in the catalog.
- [ ] **Objective 3.2 — Domain-Specific Leverage Leaves:**
  - Build and publish high-leverage single-focus skill leaves:
    - **Browser Automation Pack:** Advanced CDP manipulation, anti-bot evasion, session persistence, visual element targeting.
    - **Data Pipeline Pack:** Automated spreadsheet engineering, parquet transformations, SQLite/Turso mirrors.
    - **System Automation Pack:** Multi-agent coordination, persistent terminal management, local process supervision.
- [ ] **Objective 3.3 — Experience-Grade OpenViking Sync (opt-in):**
  - Sync only expensive-to-reconstruct experience into OpenViking: decisions, failed approaches, recurring edge cases, hard-won lessons.
  - Never auto-duplicate locally available source repositories or generated capsules; corpus inventory is probed at runtime (`membrowse`), not frozen.

---

## ⚙️ Pillar 4 Objectives: Enforce Code Quality Mechanically

> *"Anything that is mechanical, predictable, or deterministic — create tests for it."*

### Tactical Objectives:
- [ ] **Objective 4.1 — Expand Universal Quality Pack:**
  - Continuously enhance the pi-template repo's `scripts/quality-gate.py`, `scripts/dead-code.py`, `scripts/repo-hygiene.py`, and `scripts/check-integrity.py` (at `~/.agents (absorbed from the retired pi-template repo)`):
    - Add detection for circular import dependencies.
    - Add detection for orphaned images, attachments, and scratch files.
    - Add schema validation for all JSON and YAML configs.
- [ ] **Objective 4.2 — Transactional Mutation Boundaries (opt-in):**
  - Keep Pi Fabric's Schema transaction loop (`schema.hypothesize` $\to$ `verify` $\to$ `commit`) available for work that needs transactional/postcondition guarantees (enforce mode, explicit request, or postcondition-critical tasks) without making it a universal prerequisite for every reversible edit.
- [ ] **Objective 4.3 — Modular Language Quality Leaves:**
  - Maintain reusable, copyable skill leaves for downstream clones (each a `*-foundation`-canonical capsule set):
    - python-coding-practices  (pytest, mypy, ruff, bandit).
    - typescript-coding-standards (tsc, biome, effect-ts lint, vitest).
    - rust-coding-practices (cargo clippy, cargo audit, cargo test).

---

## 🧪 Test & Gate Methodology Objectives: Catch-First Verification

> *"A test is only a good test if it can properly CATCH — a passing test means nothing."*

### Tactical Objectives:
- [ ] **Objective 5.1 — Catch-First Enforcement in Core Slash Commands:**
  - Enforce the 5-Step Catch-First Protocol in `/fix` and `/ship`:
    - Require pre-fix **RED** test output evidence before code edits are permitted.
    - Require post-fix **GREEN** test output evidence before completion claims.
- [ ] **Objective 5.2 — Active Test Inventory Ledger:**
  - Maintain an indexed test catalog (`tests/README.md` and `tests/harness/README.md`) tracking which invariant categories and bug classes are defended by each test fixture.
  - Expand existing broad tests whenever an uncaught defect surfaces, rather than creating duplicate test suites.
- [ ] **Objective 5.3 — Scratch Tool Promotion Pipeline:**
  - Periodically scan `.pi/work/` and scratch directories; whenever an ad-hoc script is used more than once, refactor and promote it to the project's `scripts/` as a permanent project tool.

---

## 🔄 Tracking & Execution Cadence

These objectives are reviewed and updated during each major development milestone:
1. **Continuous Execution:** Automated cron marathons (e.g. `memory-graph-drain-marathon`) autonomously drive Pillar 1 & 3 objectives.
2. **Interactive Sessions:** Developers and coding agents use these objectives to prioritize prompt refinements, skill authoring, and PR conclusive loops.
3. **Durable Ledger:** Progress is recorded in `.pi/work/` ledgers and reconciled against `.pi/roadmap.md`.
