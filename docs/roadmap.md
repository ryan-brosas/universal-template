# Roadmap - current work objectives

This working backlog is reviewed at major milestones, not on a schedule.
Progress for significant multi-session work is recorded in the `goal-setup`
goal artifact and reconciled against Git and the project tracker. Its themes
follow the engineering constitution and catch-first test methodology.

## Summary

| Pillar / methodology | Strategic objective                                                                       | Marker                                                                          |
| -------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Ground truth         | Project source first; project-local references; foundations and skills as leverage        | Every active project grounds claims in actual source, tests, and runtime probes   |
| Steer outcomes       | Frictionless conclusive PR loop with mechanical gate boundaries                           | Fast CI checks, zero behavioral prompt bloat                                    |
| Stack leverage       | Threshold-driven skill capture; experience-grade OpenViking sync (opt-in)                 | Recurring wins become skills when they prove out                                |
| Mechanical quality   | Gates for demonstrated deterministic regressions, where value exceeds false-positive cost | Known regression classes are mechanically defended where practical              |
| Test methodology     | Catch-first verification (reproducible RED, then GREEN)                                   | Strongest available evidence per defect class                                   |

## 1. Ground truth

- **Reference-driven prior art (replaces mass ingestion).** Useful external
  repositories become project-local `reference/<repo>/` checkouts: read source
  and tests, adopt, adapt, or omit. `foundation-pack/` holds accumulated
  implementation foundations (architecture, patterns, seams) separate from
  the active skill catalog; create or expand one only when reusable
  understanding is cheaper to retrieve than to re-derive. Active owned projects
  stay in project source; completion creates no ingestion or mining backlog.
  Only an explicit user decision after a stable milestone may promote reusable
  understanding. Absorbed, stale, or low-value foundations may be pruned.
- **Reference contract adherence.** The durable contract lives with
  `reference-driven-development` at
  `skills/reference-driven-development/references/contract.md`.
  Project-local prior art lives at `<project>/reference/` and
  `<project>/reference/web/`; do not confuse the two trees.
- **Automated code-graph context discovery.** Before planning or editing,
  query the nearest sufficient source: direct code, Fovea (active-project
  structure), or an explicitly retained Codebase Memory entry (cross-repo prior
  art). Do not auto-index current projects. One primary route per question;
  escalate only on a named gap.

## 2. Steer outcomes, not behavior

- **System prompt and AGENTS.md de-cluttering.** Keep auditing `AGENTS.md`,
  host-rendered agent prompts, and this repo's policy docs: strip restrictive
  behavioral rules, and replace them with outcome contracts, binary pass/fail
  conditions, and mechanical validator commands.
- **Fast conclusive PR loop.** Keep this repo's CI jobs (catalog gates, repo
  hygiene, policy consistency, pr-title) fast and conclusive, with
  machine-readable annotations and auto-fix triggers on pull requests.
- **Demonstrated-regression gates.** Promote deterministic regression classes
  into low-false-positive gates when correctness and maintenance value exceed
  the cost. Aesthetic preference alone is not a valid gate.

## 3. Build stacked advantage

- **Threshold-driven skill capture.** At a meaningful milestone, classify
  recurring wins through `leverage-capture` (code, reference, gate, skill,
  memory, or not worth saving). Capture is threshold-driven, never automatic;
  one-off details recoverable from source stay in code.
- **Domain-specific skill leaves (as demand appears).** High-value
  single-focus leaves for downstream clones, whether browser automation,
  data pipelines, or multi-agent coordination. Build on observed need, not
  speculation.
- **Experience-grade OpenViking sync (opt-in).** Sync only
  expensive-to-reconstruct experience: decisions, failed approaches, recurring
  edge cases, hard-won lessons. Never auto-duplicate locally available source
  repositories or generated capsules; corpus inventory is probed at runtime.

## 4. Enforce mechanically

- **Expand the catalog gate suite.** Grow the validator scripts
  (`scripts/skill-validator.py`, `catalog-quality.py`,
  `repo-hygiene.py`, `dead-code.py`, `policy-consistency.py`,
  `style-lint.py`) with structural skill-visibility checks, dangling
  cross-skill reference detection, and portable-path validation for new config
  surfaces.
- **Transactional mutation boundaries (opt-in).** Host-specific execution
  guards (pi: `skills/fabric-native-execution/` and project or `~/.pi/`
  config) stay opt-in for work that needs transactional or postcondition
  guarantees, not a universal prerequisite for every reversible edit.
- **Modular language quality leaves (as needed).** Reusable, copyable practice
  leaves for downstream clones following the reference contract: Python
  (pytest, mypy, ruff, bandit), TypeScript (tsc, biome, vitest), Rust (cargo
  clippy, cargo audit, cargo test).

## 5. Catch-first test methodology

- **Catch-first verification.** A reproducible defect gets a RED (pre-fix
  failure) in the project's fix or ship suite, then the fix, then GREEN. A
  non-reproducible defect gets the strongest available failure evidence, the
  closest meaningful regression boundary, and deterministic verification
  afterward. Never fabricate a failing test to satisfy process.
- **Expand tests on escape.** When an uncaught defect surfaces, expand the
  existing broad test that should have caught it instead of creating a
  duplicate suite.
- **Scratch tool promotion.** When a scratch script earns reuse, promote it
  into `scripts/` as a permanent project tool. No scheduled analysis marathons.

## Tracking

1. Recurring objectives are driven by explicit scheduled work the user
   requested; no autonomous marathons by default.
2. Interactive sessions use this file to prioritize prompt refinements, skill
   authoring, and PR loops.
3. Durable progress for significant multi-session work lives in the
   `goal-setup` goal artifact, reconciled against Git and the project tracker.
