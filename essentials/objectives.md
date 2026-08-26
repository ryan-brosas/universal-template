# Essentials Objectives: Strategic & Tactical Implementation Goals

A concrete, actionable set of objectives derived directly from the four pillars
and test methodology of our operating philosophy. These objectives drive our
roadmap, skill development, testing harness, automation pipelines, and cron marathons.

---

## 🎯 Master Objective Summary

| Pillar / Methodology | Primary Strategic Objective | Target Milestone |
| :--- | :--- | :--- |
| **Pillar 1: Ground Truth** | 100% Inspiration Ingestion into `pack-foundations` via Two-Pass Learning | Full squeeze of all 73 inspo repos |
| **Pillar 2: Steer Outcomes** | Frictionless Conclusive PR Loop with Mechanical Gate Boundaries | Sub-30s CI checks, zero behavioral prompt bloat |
| **Pillar 3: Stack Leverage** | Automated Post-Session Skill Capture & Tripled-Layer Viking Memory | Autonomous `/learn` workflow and OpenViking sync |
| **Pillar 4: Mechanical Quality** | Universal + Language-Specific Quality Packs with Unbypassable Gates | Zero-defect automated gating across all projects |
| **Test Methodology** | Catch-First Verification Standard (Un-fixed RED $\to$ Fixed GREEN) | Mandatory pre-fix failure proofs on all bugfixes |

---

## 🏛️ Pillar 1 Objectives: Ground Truth & Guiding Small Models

> *"A small model lacks knowledge, not capacity. Give it ground truth to work from."*

### Tactical Objectives:
- [ ] **Objective 1.1 — Complete Inspiration Ingestion (43 Repos Remaining):**
  - Execute the Two-Pass Learning Protocol on all remaining unsqueezed repos in `/mnt/hdd/utopia/inspo`.
  - **Tier 1 Targets:** `locoagent` (21k), `cuga-agent` (21k), `nocodb` (187k), `pipeshub-ai` (127k), `teable` (53k), `grist-core` (27k), `dub` (24k).
  - **Tier 2 Targets:** `modelcontextprotocol` (12k), `servers`, `vitest` (16k), `nest` (13k), `rsbuild` (14k), `relaticle` (9k), `nodebestpractices` (6k).
  - **Tier 3 Targets:** Combined `linkedin-scrapers-foundation` mining all ~14 scraper repos into a unified suite.
- [ ] **Objective 1.2 — 100% `<!-- capsule-v2 -->` Migration:**
  - Audit all references across `pack-foundations` and ensure 100% adherence to the capsule-v2 contract (Source/Question, HEAD line numbers, Signature, Data Shape, decisive source, Flow, Invariant, direct test Probe, Retrieve query, Verdict).
  - Eliminate all remaining legacy capsule-v1 markdown files.
- [ ] **Objective 1.3 — Automated Code Graph Context Prewalk:**
  - Standardize prewalk routines so that before planning or editing, agents automatically query `codegraphcontext` (for active project symbols) or Codebase Memory (for external prior art) rather than drafting from blank context.

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
- [ ] **Objective 3.1 — Automated Post-Session Skill Capture:**
  - Implement a dedicated skill-harvesting prompt workflow (`/learn` or post-session hook) that extracts newly solved edge cases, platform quirks, and error recovery patterns into new skill drafts at session close.
- [ ] **Objective 3.2 — Domain-Specific Leverage Packs:**
  - Build and publish high-leverage skill packs:
    - **Browser Automation Pack:** Advanced CDP manipulation, anti-bot evasion, session persistence, visual element targeting.
    - **Data Pipeline Pack:** Automated spreadsheet engineering, parquet transformations, SQLite/Turso mirrors.
    - **System Automation Pack:** Multi-agent coordination, persistent terminal management, local process supervision.
- [ ] **Objective 3.3 — Tripled-Layer Viking Memory Sync:**
  - Automatically sync newly generated skills and foundation capsules into OpenViking (`/mnt/hdd/openviking/data`), maintaining:
    - *Layer 1:* Searchable capsule resources.
    - *Layer 2:* Living work records and process runbooks.
    - *Layer 3:* Durable pattern memories and meta-lessons.

---

## ⚙️ Pillar 4 Objectives: Enforce Code Quality Mechanically

> *"Anything that is mechanical, predictable, or deterministic — create tests for it."*

### Tactical Objectives:
- [ ] **Objective 4.1 — Expand Universal Quality Pack:**
  - Continuously enhance the pi-template repo's `scripts/quality-gate.py`, `scripts/dead-code.py`, `scripts/repo-hygiene.py`, and `scripts/check-integrity.py` (at `/home/utopia/work/project/pi-template`):
    - Add detection for circular import dependencies.
    - Add detection for orphaned images, attachments, and scratch files.
    - Add schema validation for all JSON and YAML configs.
- [ ] **Objective 4.2 — Unbypassable Mutation Boundaries:**
  - Preserve the strict Schema commit loop (`schema.hypothesize` $\to$ `verify` $\to$ `commit`) in Pi Fabric so that no agent can write unverified code or pollute unrelated working-tree files.
- [ ] **Objective 4.3 — Modular Language Quality Packs:**
  - Maintain reusable, copyable quality pack templates for downstream clones:
    - `pack-python-quality` (pytest, mypy strict, ruff, bandit).
    - `pack-typescript-quality` (tsc, biome, effect-ts lint, vitest).
    - `pack-rust-quality` (cargo clippy, cargo audit, cargo test).

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
