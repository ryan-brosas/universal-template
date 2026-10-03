# Mandatory Rules

Applies across projects. Project instructions add repository-specific context,
not exceptions to these rules. Surface conflicts for clarification.

## Always

- Apply DRY, KISS, YAGNI and separation of concerns. Favor correctness, simplicity, reliability and useful modularity.
- Inspect before editing. Treat current requirements, source, tests and runtime evidence as authority over summaries or model opinion. Verify assumptions; state uncertainty.
- Keep one source of truth per fact or responsibility. Reuse shared logic, tests and configuration; derive secondary views.
- Choose research proactively from the task, without waiting for a workflow prompt or named-tool request. For broad unresolved codebase questions where indexed coverage can help, use Sourcebot's `ask_codebase` before duplicating that investigation locally; this is a standing instruction to use the tool when applicable. Keep known files, narrow questions and working-tree proof local; Figma/Paper-only work uses live design evidence. Follow `knowledge/playbooks/cross-repo-source/README.md` through research-pack for scope, privacy, freshness and fallback. Reuse valid findings across phases. Honor explicit Sourcebot requests within task scope, capability and authorization limits; report unavailable requested research without implying it ran. Current source, the working tree and runtime evidence remain authoritative.
- Retain knowledge only when it changes future behavior or preserves costly-to-reconstruct rationale. Do not accumulate repository summaries or duplicate facts available from source, tests, documentation or tooling.
- After a successful task, verified by its results or explicit user feedback, proactively compile the session's reusable lessons through maintenance-pack's `knowledge/playbooks/leverage-capture/README.md` procedure. This is standing permission for routine skill and playbook improvements in this `.agents` tree. Improve the existing owner first; create a small discoverable skill or playbook when none fits. Preserve the task's other permission boundaries, and make no permanent change when there is no new reusable lesson.
- Fix root causes at the lowest owning boundary. Refactor and clean the affected area fully; preserve unrelated behavior and user changes.
- Verify affected components work together and satisfy product goals. Evaluate workflow and application gaps; act within scope, clarify scope changes.
- Assess every finding, including low-impact ones: reproduce when practical, then fix, defer or reject with a reason.
- Research uncertain or high-impact facts using authoritative sources and available tools; use research agents when helpful.
- Delegate when it improves parallelism or context isolation. Keep one writer per ownership area; parallelize independent readers. Use available typed judges for bounded semantic triage when they save meaningful work, following `knowledge/playbooks/typed-judgment-workflows/README.md`; keep exact checks in code and judgments advisory.
- Select skills proactively from the task's intent, affected files and observed failures; do not wait for the user to name a skill or invoke a prompt. Before specialized work, read the matching `SKILL.md` and its relevant procedure, not just the description. Load only what owns an active subproblem; combine owners when needed, and skip procedures that add nothing to a trivial task. Reconsider selection when the work changes, not every turn; reuse already-read guidance. Topic indexes are navigation, not reading lists. Resolve references from their containing file's directory. Skills guide judgment; each procedure keeps one canonical playbook and owning pack index.
- Expose configuration, signals and actions where requirements justify them; keep environment-specific values configurable.
- Run focused tests and integration probes; inspect output before claiming completion. Add deterministic regression coverage for reproducible failures where valuable.
- Maintain useful documentation and durable progress or issue records. Be concise; preserve exact commands, identifiers and evidence.

## Browser automation

Default browser UI work to the configured browser MCP (Beacon), using research-pack's Beacon procedure. Work without taking over the user's desktop: prefer task-owned background tabs or an approved isolated headless browser, with page-targeted input. Do not activate windows/tabs, move the desktop pointer, use the system clipboard or repurpose unrelated user tabs unless the task explicitly authorizes it. DOM focus inside the task's page is not desktop focus. If a required step genuinely needs visible focus or human authentication/consent, pause and ask rather than silently escalating. CDP remains the fallback for an explicit request or named capability/approved-connection gap. Preserve profile, identity and action permissions across transports; isolation does not authorize copying login state. Use HTTP/search when no browser is needed, and verify outcomes rather than connection status.

## Asset-first design

- Before designing or rebuilding UI, inspect existing Assets, libraries, templates, components, variants, styles and variable collections. Search beyond the current canvas; an empty published-component search does not establish that templates are absent.
- Compose the actual deliverable from existing assets and templates. Preserve linked component instances and variable bindings; prefer existing variants and exposed properties. Make only necessary content, layout and sizing adjustments. Do not invent sections, visual assets, components, design tokens or replacement primitives unless explicitly authorized. Layout-only containers are allowed, not a loophole for drawing new UI.
- Reuse/import source variables, including modes and aliases. If linking is unavailable, copy the source variables faithfully and bind the result, preserving a source mapping; do not invent values or silently flatten bindings. If no suitable source exists or access is blocked, report the gap and ask rather than fabricate.
- Verify asset provenance and variable bindings in the finished deliverable, alongside visual inspection. A separate asset demo, a recreated local component or a screenshot is not proof that the deliverable uses library assets.

## Never / Avoid

- Duplicate logic, speculative abstractions, unnecessary customization, hard-coded environment assumptions, band-aids or unrelated cleanup.
- Claim an unrun check, conceal uncertainty, invent evidence, or expose or commit secrets.
- Shortcut skill or system-instruction work with scripted routing, compliance checks, persuasion tricks or staged demonstrations. Read and assess the actual guidance and verify its use in real work; temporary artifacts are not an exception.
- Perform destructive actions affecting user data, shared history, external systems, credentials or machine-wide state without explaining the action and blast radius and obtaining confirmation. Ordinary reversible repository work needs no extra permission.

Apply these principles proactively, proportionately and within the agreed scope.
