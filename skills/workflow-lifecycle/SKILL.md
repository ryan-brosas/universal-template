---
name: workflow-lifecycle
description: "Use when running pi lifecycle workflows as a skill - workspace init for persistent or governed workspaces, learning lessons into skills, cross-cutting pattern audits, pre-claim verification, or workspace GC - with need-driven retrieval (one primary route, escalate on a named gap, stop when evidence is sufficient) so prior skill-mining context is reused instead of starting cold. NOT for one-off edits or plain commands."
---

# Workflow Lifecycle (init / learn / audit / verify / gc)

## Core Principle

One skeleton for every lifecycle workflow: verify capability, retrieve context as needed, preview read-only, mutate through the session's authority mode, verify the artifact, record evidence. Host-neutral by default; MCP-aware when the toolset offers it.

## When to Use / NOT

- Use when the user asks to initialize or re-govern a workspace (init), distill a session lesson into a skill (learn), audit a cross-cutting pattern (audit), verify before claiming done (verify), or clean up (gc).
- NOT when: a one-off edit or a plain command run with no governance angle.

## The Commands

| Command | Deliverable | Reference |
|---|---|---|
| init | AGENTS.md + .pi context artifacts, idempotently | references/init.md |
| learn | A new/updated SKILL.md in the global catalog | references/learn.md |
| audit | A graded, prioritized pattern report | references/audit.md |
| verify | A gate-backed READY / NEEDS-WORK verdict | references/verify.md |
| gc | Workspace hygiene cleanup | references/gc.md |
| dev loop | the daily working loop — init once, AGENTS.md as spine, scoped implementation with gates, documents AFTER implementation, lessons distilled via the learn command | references/dev-loop.md |

## Context sources (need-driven, not an ordered ritual)

Pick the one source that answers the question; escalate only after a named gap; stop when evidence is sufficient. `evidence-router` is the canonical routing policy. The registered inventory:

- **Codebase Memory** (`codebase_memory.*`, project graph): architecture, definitions, callers/callees, traces. An index, not source of truth — probe `index_status` / `check_index_coverage` before citing coverage; never cite a graph you did not verify covers the code.
- **OpenViking** (`extensions.memsearch` / `memfind` / `memgrep` / `memread`, plus `membrowse` / `memglob` for structure): semantic search, exact symbols/errors, targeted reads over the mined corpora (`viking://resources/*-foundation`, `llm-repo-learning-*`). This is how prior skill-mining context is reused.
- **Context7** (`context7.resolve-library-id` → `context7.query-docs`): current library documentation + code examples; one concept per call, max 3 calls per question.
- **Exa** (web search): current versions/trends/upstream facts not in any local graph or corpus.
- **DeepWiki** (`deepwiki.get-deepwiki-index` → `get-deepwiki-page`): architecture pages for large OSS repos.

Which sources actually exist depends on what MCP servers the host registered. Probe first (registry check), skip missing sources with a note — never fabricate a reference or cite a hit you did not verify. Read the actual source before implementing or making load-bearing claims; hits are pointers, not proofs.

## Mutation boundary

- Research and previews are read-only.
- Normal reversible writes (artifact, skill file, catalog) inside the current git workspace need no repeated approval; verify them like any code change.
- Run the Schema loop in one fabric_exec (`schema.hypothesize` with evidence → `schema.verify` → `schema.commit` with declared operations and postconditions) only when the session runs Schema enforce mode, the user invokes a Fabric Schema mechanism, or the task explicitly needs transactional/postcondition guarantees. Schema enforce mode disables `/fabric prewalk` — never switch modes silently.
- Outside Pi Fabric, apply the global mutation boundaries in `AGENTS.md` (dangerous actions need confirmation).

## Skill Result Contract

```
<skill_result>
  <skill>workflow-lifecycle</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>capability probes, retrieval digest, artifact paths, gate outputs</evidence>
  <artifacts>files written / commands run</artifacts>
  <risks>unindexed context, clobbered user content</risks>
</skill_result>
```

## References

- `references/init.md` - init phases, idempotency matrix, quality contract
- `references/learn.md` - lesson distillation and catalog path
- `references/audit.md` - pattern discovery and severity grading
- `references/verify.md` - cache, completeness, gates
- `references/gc.md` - hygiene contract
- `references/mcp-context.md` - context source inventory recipes (graph, corpus, library docs, web, wiki)
- `references/dev-loop.md` - the default daily working loop (init once, scoped work with gates, documents after implementation, essentials enforced)

## Red Flags

Citing a graph that was not verified to cover the code; fabricating a retrieval hit because a source is missing; mutating outside the session's authority mode; treating prose review as verification.

## Verification

Each command's named deliverable exists on disk (artifact paths in the skill result); capability probes show which context sources are actually registered; when the Schema loop was used, its postconditions from `schema.commit` hold.
