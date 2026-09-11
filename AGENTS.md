# Mandatory Rules

Applies across projects. Project instructions add repository-specific context,
not exceptions to these rules. Surface conflicts for clarification.

## Always

- Apply DRY, KISS, YAGNI and separation of concerns. Favor correctness, simplicity, reliability and useful modularity.
- Inspect before editing. Treat current requirements, source, tests and runtime evidence as authority over summaries or model opinion. Verify assumptions; state uncertainty.
- Keep one source of truth per fact or responsibility. Reuse shared logic, tests and configuration; derive secondary views.
- Resolve code questions from current source and tests. Use direct source, Git and normal development tools for the current repository; Sourcebot for code across intentionally indexed repositories; GitHub to discover unknown implementations; official docs or Context7 for library documentation. Choose the cheapest sufficient evidence; no tool is a mandatory first step.
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
