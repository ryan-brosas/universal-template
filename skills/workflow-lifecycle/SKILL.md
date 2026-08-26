---
name: workflow-lifecycle
description: "Use when running pi lifecycle workflows as a skill - workspace init, learning lessons into skills, cross-cutting pattern audits, pre-claim verification, or workspace GC - and when decisions should first draw context from the five-source plane: Codebase Memory (index_status, search_graph), OpenViking (memsearch, memgrep, memread), Context7 library docs, Exa web, and DeepWiki architecture pages, so prior skill-mining context is reused instead of starting cold."
---

# Workflow Lifecycle (init / learn / audit / verify / gc)

## Core Principle

One skeleton for every lifecycle workflow: verify capability, retrieve context, preview read-only, mutate only under Schema or explicit approval, verify the artifact, record evidence. Host-neutral by default; MCP-aware when the toolset offers it.

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
| dev loop | the daily working loop — init once, AGENTS.md as spine, slice-by-slice development, documents AFTER implementation, lessons distilled via /learn | references/dev-loop.md |

## Shared context plane (five sources)

Retrieval is a first-class phase before any answer or write. Probe what exists, then use the sources in order:

1. **Codebase Memory** (`codebase_memory.*`, project graph): probe `index_status` / `check_index_coverage` first (read the parse_partial/skipped coverage report), then `search_graph` / `query_graph` / `trace_path` / `get_code_snippet`. Never cite a graph you did not verify covers the code.
2. **OpenViking** (`extensions.memsearch` / `memfind` / `memgrep` / `memread`, plus `membrowse` / `memglob` for structure): semantic search, discovery, exact symbols/errors, targeted reads over the mined corpora (`viking://resources/*-foundation`, `llm-repo-learning-*`). This is how prior skill-mining context is reused.
3. **Context7** (`context7.resolve-library-id` → `context7.query-docs`): current library documentation + code examples; one concept per call, max 3 calls per question.
4. **Exa** (web search): current versions/trends/upstream facts not in any local graph or corpus.
5. **DeepWiki** (`deepwiki.get-deepwiki-index` → `get-deepwiki-page`): architecture pages for large OSS repos.

Which sources actually exist depends on what MCP servers the host registered. Probe first (registry check), and skip missing sources with a note — never fabricate a reference or cite a hit you did not verify.

## Mutation boundary

- Research and previews are read-only.
- Any write (artifact, skill file, catalog) goes through the Schema loop in one fabric_exec: schema.hypothesize (evidence) to schema.verify to schema.commit with declared files and postconditions; when the mode is not enforce, propose exact files and get approval.

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

- references/init.md - init phases, idempotency matrix, quality contract
- references/learn.md - lesson distillation and catalog path
- references/audit.md - pattern discovery and severity grading
- references/verify.md - cache, completeness, gates
- references/gc.md - hygiene contract
- references/mcp-context.md - five-source retrieval recipes (graph, corpus, library docs, web, wiki)
- references/dev-loop.md - the default daily working loop (init once, slice by slice, documents after implementation, essentials enforced)