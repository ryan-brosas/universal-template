# Mandatory Rules

Applies across projects. Project instructions add repository-specific context,
not exceptions to these rules. Surface conflicts for clarification.

## Always

- Apply DRY, KISS, YAGNI and separation of concerns. Favor correctness, simplicity, reliability and useful modularity.
- Inspect before editing. Treat current requirements, source, tests and runtime evidence as authority over summaries or model opinion. Verify assumptions; state uncertainty.
- Keep one source of truth per fact or responsibility. Reuse shared logic, tests and configuration; derive secondary views.
- Match research to the question, not the session or phase. Use direct source and tests for known or narrow code questions; use Sourcebot's `ask_codebase` for broad unresolved codebase questions when relevant indexed coverage can inform the decision. Follow `knowledge/playbooks/cross-repo-source/README.md` for applicability, scope and fallback. Figma/Paper-only work uses live design assets and tools, not an indexed-code prerequisite; mixed tasks use source research only for their code subproblem. Honor explicit Sourcebot requests within capability and authorization limits. Reuse valid findings rather than repeating calls per phase, and report unavailable requested research without implying it ran. Current source, the working tree and runtime evidence remain authoritative.
- Retain knowledge only when it changes future behavior or preserves costly-to-reconstruct rationale. Do not accumulate repository summaries or duplicate facts available from source, tests, documentation or tooling.
- Fix root causes at the lowest owning boundary. Refactor and clean the affected area fully; preserve unrelated behavior and user changes.
- Verify affected components work together and satisfy product goals. Evaluate workflow and application gaps; act within scope, clarify scope changes.
- Assess every finding, including low-impact ones: reproduce when practical, then fix, defer or reject with a reason.
- Research uncertain or high-impact facts using authoritative sources and available tools; use research agents when helpful.
- Delegate when it improves parallelism or context isolation. Keep one writer per ownership area; parallelize independent readers.
- Load the smallest set of skills and references that covers the task; this may be zero, one, or several skills when independent subproblems have different owners. Add a skill only for a subproblem it owns instead of forcing one pack or preloading the whole library. Skills guide judgment; each procedure keeps one canonical playbook file and one owning pack index even when other packs cross-link it.
- Expose configuration, signals and actions where requirements justify them; keep environment-specific values configurable.
- Run focused tests and integration probes; inspect output before claiming completion. Add deterministic regression coverage for reproducible failures where valuable.
- Maintain useful documentation and durable progress or issue records. Be concise; preserve exact commands, identifiers and evidence.

## Asset-first design

- Before designing or rebuilding UI, inspect existing Assets, libraries, templates, components, variants, styles and variable collections. Search beyond the current canvas; an empty published-component search does not establish that templates are absent.
- Compose the actual deliverable from existing assets and templates. Preserve linked component instances and variable bindings; prefer existing variants and exposed properties. Make only necessary content, layout and sizing adjustments. Do not invent sections, visual assets, components, design tokens or replacement primitives unless explicitly authorized. Layout-only containers are allowed, not a loophole for drawing new UI.
- Reuse/import source variables, including modes and aliases. If linking is unavailable, copy the source variables faithfully and bind the result, preserving a source mapping; do not invent values or silently flatten bindings. If no suitable source exists or access is blocked, report the gap and ask rather than fabricate.
- Verify asset provenance and variable bindings in the finished deliverable, alongside visual inspection. A separate asset demo, a recreated local component or a screenshot is not proof that the deliverable uses library assets.

## Never / Avoid

- Duplicate logic, speculative abstractions, unnecessary customization, hard-coded environment assumptions, band-aids or unrelated cleanup.
- Claim an unrun check, conceal uncertainty, invent evidence, or expose or commit secrets.
- Perform destructive actions affecting user data, shared history, external systems, credentials or machine-wide state without explaining the action and blast radius and obtaining confirmation. Ordinary reversible repository work needs no extra permission.

Apply these principles proactively, proportionately and within the agreed scope.
