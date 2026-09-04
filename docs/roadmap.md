# Roadmap - current work objectives

This working backlog is reviewed at major milestones, not on a schedule.
Progress is normally recoverable from source, Git, the project tracker, and project-scoped session evidence. A compact `goal-setup` post-code work record is reserved for a roughly four-day-or-longer run with meaningful recovery/handoff needs, or an explicit user, project, or external coordination requirement. Its themes follow the engineering constitution and catch-first test methodology.

## Summary

| Pillar / methodology | Strategic objective                                                                       | Marker                                                                          |
| -------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Ground truth         | Project source first; project-local references; foundations and skills as leverage        | Every active project grounds claims in actual source, tests, and runtime probes   |
| Steer outcomes       | Frictionless conclusive PR loop with mechanical gate boundaries                           | Fast CI checks, zero behavioral prompt bloat                                    |
| Stack leverage       | Threshold-driven skill capture; event-sourced context projections (opt-in)                | Recurring wins become skills when they prove out                                |
| Mechanical quality   | Gates for demonstrated deterministic regressions, where value exceeds false-positive cost | Known regression classes are mechanically defended where practical              |
| Test methodology     | Catch-first verification (reproducible RED, then GREEN)                                   | Strongest available evidence per defect class                                   |

## Context-provable baseline

The baseline treats context as an explicit publication contract: the compact
global constitution plus tracked, visible entry metadata is static context.
Internal, manual, vendor, and foundation leaves are cold and on demand. CI reads
one canonical config to gate the constitution, hot metadata, combined budget,
and zero set overlap. Host payload evidence and dynamic MCP schema costs are
versioned in `docs/context-measurements.json`; the six-server MCP file is a
registry with an empty minimal profile, not an always-on connection set. Strict YAML parsing,
Git-tracked hygiene, vendor/session exclusions, atomic prompt adapters, and
fail-closed CDP text persistence protect the same boundary. Re-probe host
versions and payloads when those integrations change.

## 1. Ground truth

- **Reference-driven prior art (replaces mass ingestion).** Useful external
  repositories become project-local `reference/<repo>/` checkouts: read source
  and tests, adopt, adapt, or omit. `skills/` is the one capability tree;
  `kind: foundation` leaves hold accumulated, source-specific implementation
  evidence (architecture, patterns, seams) while remaining excluded from the
  operational catalog and startup metadata. Create or expand one only when reusable
  understanding is cheaper to retrieve than to re-derive. Active owned projects
  stay in project source; completion creates no ingestion or mining backlog.
  Only an explicit user decision after a stable milestone may promote reusable
  understanding. Absorbed, stale, or low-value foundations may be pruned.
  **Foundation freeze.** No new repository-derived foundation is created
  merely because a repository was studied; a study pass recommends
  ADOPT, ADAPT, or OMIT and creates no artifact. An existing leaf is
  triaged only when a real project retrieves it: keep it when it supplied
  a non-obvious invariant that was expensive to reconstruct, and retire
  source summaries, unused encyclopedic maps, and material recoverable
  from source or Codebase Memory. Git history preserves retired material;
  do not move it into another searchable archive.
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
  recurring wins through `leverage-capture` (code, reference, foundation,
  gate, skill, project note, or not worth saving). Capture is threshold-driven, never automatic;
  one-off details recoverable from source stay in code.
- **Domain-specific skill leaves (as demand appears).** High-value
  single-focus leaves for downstream clones, whether browser automation,
  data pipelines, or multi-agent coordination. Build on observed need, not
  speculation.
- **Event-sourced context projections (opt-in).** Retrieve bounded evidence
  from current source and project-scoped session history; generate reflections
  and context views on demand; promote only accepted code, gates, skills, or
  rare minimal notes. Optional caches such as OpenViking remain rebuildable,
  non-authoritative, and never synchronized or injected automatically;
  corpus inventory is probed at runtime.

## 4. Enforce mechanically

- **Keep publication checks exact.** Deterministic validation covers structured
  data, names, paths, references, generated parity, secret patterns, and safe
  mutation. Models review policy meaning, prose, skill usefulness, evidence
  sufficiency, and architectural tradeoffs from current source and runtime facts.
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
3. Durable progress stays in source, Git, and the project tracker. Raw project-scoped session history preserves historical work evidence. Use a compact `goal-setup` post-code work record only for qualified long-running or handoff-heavy work, or an explicit user, project, or external coordination requirement; reconcile it against Git and the project tracker.
