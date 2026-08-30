# Essentials Objectives: Strategic & Tactical Implementation Goals

A concrete, actionable set of objectives derived directly from the four pillars
and test methodology of our operating philosophy. These objectives drive our
roadmap, skill development, testing harness, automation pipelines, and cron marathons.

---

## 🎯 Master Objective Summary

| Pillar / Methodology | Primary Strategic Objective | Target Milestone |
| :--- | :--- | :--- |
| **Pillar 1: Ground Truth** | Reference-driven prior art; foundation freeze (no mass ingestion) | Every active project grounds claims in actual source, tests, and runtime probes |
| **Pillar 2: Steer Outcomes** | Frictionless Conclusive PR Loop with Mechanical Gate Boundaries | Sub-30s CI checks, zero behavioral prompt bloat |
| **Pillar 3: Stack Leverage** | Automated Post-Session Skill Capture & Tripled-Layer Viking Memory | Autonomous `/learn` workflow and OpenViking sync |
| **Pillar 4: Mechanical Quality** | Gates for demonstrated deterministic regressions, where value exceeds false-positive cost | Known regression classes are mechanically defended where practical |
| **Test Methodology** | Catch-First Verification Standard (Un-fixed RED $\to$ Fixed GREEN) | Mandatory pre-fix failure proofs on all bugfixes |

---

## 🏛️ Pillar 1 Objectives: Ground Truth & Guiding Small Models

> *"A small model lacks knowledge, not capacity. Give it ground truth to work from."*

### Tactical Objectives:
- [ ] **Objective 1.1 — Reference-Driven Prior Art (replaces mass ingestion):**
  - Useful external repositories become project-local `reference/<repo>/` checkouts — read source/tests, adopt/adapt/omit. Repo → foundation mining is **frozen** while this path is validated.
  - Deliberate foundation exceptions only: a named recurring porting question that source alone does not answer (`foundations-workflow`, one repo at a time).
  - Existing `*-foundation` leaves are preserved pending measured triage (keep / shrink / retire per `code-foundations`).
- [ ] **Objective 1.2 — Reference contract adherence:**
  - New `references/` capsules follow `references/reference-contract.md` (source, decisive excerpts, retrieval queries, verdict).
  - Existing capsules are maintained as they are touched — no bulk migration.
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
- [ ] **Objective 2.2 — Fast Conclusive PR Loop:**
  - Keep this repo's CI jobs (`catalog gates`, `repo hygiene`, `policy consistency`, `pr-title`) fast and conclusive.
  - Provide machine-readable annotations and auto-fix triggers on all pull requests.
- [ ] **Objective 2.3 — Demonstrated-Regression Gates:**
  - Promote deterministic regression classes into low-false-positive gates when correctness/maintenance value exceeds the cost.
  - Aesthetic preference is not automatically a valid mechanical gate — a gate needs a demonstrated failure class and an acceptable false-positive rate.

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
- [ ] **Objective 4.1 — Expand the catalog gate suite:**
  - Continuously enhance this repo's gate scripts (`scripts/skill-validator.py`, `scripts/catalog-integrity.py`, `scripts/catalog-quality.py`, `scripts/repo-hygiene.py`, `scripts/dead-code.py`, `scripts/policy-consistency.py`):
    - Structural skill-visibility checks (router visibility, ownership boundaries).
    - Detection for dangling cross-skill references.
    - Portable-path validation for new config surfaces.
- [ ] **Objective 4.2 — Transactional Mutation Boundaries (opt-in):**
  - Keep Pi Fabric's Schema transaction loop (`schema.hypothesize` $\to$ `verify` $\to$ `commit`) available for work that needs transactional/postcondition guarantees (enforce mode, explicit request, or postcondition-critical tasks) without making it a universal prerequisite for every reversible edit.
- [ ] **Objective 4.3 — Modular Language Quality Leaves (as needed):**
  - Maintain reusable, copyable skill leaves for downstream clones (following the reference contract):
    - python-coding-practices  (pytest, mypy, ruff, bandit).
    - typescript-coding-standards (tsc, biome, effect-ts lint, vitest).
    - rust-coding-practices (cargo clippy, cargo audit, cargo test).

---

## 🧪 Test & Gate Methodology Objectives: Catch-First Verification

> *"A test is only a good test if it can properly CATCH — a passing test means nothing."*

### Tactical Objectives:
- [ ] **Objective 5.1 — Catch-First Verification (reproducible defects):**
  - Reproducible defect → RED (pre-fix failure) → fix → GREEN (post-fix pass) in the project's fix/ship suites.
  - Non-reproducible defect → strongest available failure evidence → closest meaningful regression boundary → fix → strongest available deterministic verification. Never fabricate a failing test to satisfy process.
- [ ] **Objective 5.2 — Active Test Inventory Ledger:**
  - Maintain an indexed test catalog (`tests/README.md` and `tests/harness/README.md`) tracking which invariant categories and bug classes are defended by each test fixture.
  - Expand existing broad tests whenever an uncaught defect surfaces, rather than creating duplicate test suites.
- [ ] **Objective 5.3 — Scratch Tool Promotion Pipeline:**
  - Periodically scan `.pi/work/` and scratch directories; whenever an ad-hoc script is used more than once, refactor and promote it to the project's `scripts/` as a permanent project tool.

---

## 🔄 Tracking & Execution Cadence

These objectives are reviewed and updated during each major development milestone:
1. **Continuous Execution:** recurring objectives are driven by explicit scheduled work the user actually requested — no autonomous marathons by default.
2. **Interactive Sessions:** Developers and coding agents use these objectives to prioritize prompt refinements, skill authoring, and PR conclusive loops.
3. **Durable Ledger:** progress for significant multi-session work is recorded in the goal artifact (`goal-setup`) and reconciled against Git and the project's tracker — no global state file.
