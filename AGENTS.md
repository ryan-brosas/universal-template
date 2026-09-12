# Mandatory Rules

Applies across projects. Project instructions add repository-specific context,
not exceptions to these rules. Surface conflicts for clarification.

## Always

- Apply DRY, KISS, YAGNI and separation of concerns. Favor correctness, simplicity, reliability and useful modularity.
- Inspect before editing. Treat current requirements, source, tests and runtime evidence as authority over summaries or model opinion. Verify assumptions; state uncertainty.
- Keep one source of truth per fact or responsibility. Reuse shared logic, tests and configuration; derive secondary views.
- Resolve code questions from authoritative source and tests. Prefer direct retrieval for narrow lookups and delegated research for broad investigations to keep exploration out of the main context. Use Sourcebot for intentionally indexed code, including the current repository when revision coverage fits; local tools or agents for working-tree-specific questions; GitHub to discover unknown implementations; official docs or Context7 for library documentation. Verify decision-critical findings against relevant source and runtime evidence. Optimize whole-task context, latency and correctness; no tool is a mandatory first step.
- Retain knowledge only when it changes future behavior or preserves costly-to-reconstruct rationale. Do not accumulate repository summaries or duplicate facts available from source, tests, documentation or tooling.
- Fix root causes at the lowest owning boundary. Refactor and clean the affected area fully; preserve unrelated behavior and user changes.
- Verify affected components work together and satisfy product goals. Evaluate workflow and application gaps; act within scope, clarify scope changes.
- Assess every finding, including low-impact ones: reproduce when practical, then fix, defer or reject with a reason.
- Research uncertain or high-impact facts using authoritative sources and available tools; use research agents when helpful.
- Delegate when it improves parallelism or context isolation. Keep one writer per ownership area; parallelize independent readers.
- Load only relevant skills and references, never the whole library. Skills guide judgment; procedures belong in their owning playbooks.
- Expose configuration, signals and actions where requirements justify them; keep environment-specific values configurable.
- Run focused tests and integration probes; inspect output before claiming completion. Add deterministic regression coverage for reproducible failures where valuable.
- Maintain useful documentation and durable progress or issue records. Be concise; preserve exact commands, identifiers and evidence.

## Never / Avoid

- Duplicate logic, speculative abstractions, unnecessary customization, hard-coded environment assumptions, band-aids or unrelated cleanup.
- Claim an unrun check, conceal uncertainty, invent evidence, or expose or commit secrets.
- Perform destructive actions affecting user data, shared history, external systems, credentials or machine-wide state without explaining the action and blast radius and obtaining confirmation. Ordinary reversible repository work needs no extra permission.

Apply these principles proactively, proportionately and within the agreed scope.
