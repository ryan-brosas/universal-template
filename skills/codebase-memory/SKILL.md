---
name: codebase-memory
description: "Use when navigating, indexing, tracing, or comparing local and inspiration repositories through the Codebase Memory MCP knowledge graph."
disable-model-invocation: true
---

# Codebase Memory

Use the `codebase-memory` MCP as the primary structural code-discovery surface.
Its graph is an index, not source of truth: confirm exact code in the JetBrains IDE
or direct source before editing or making exhaustive claims.

## Workflow

1. Connect to the `codebase-memory` MCP and read its server instructions.
2. Call `codebase-memory_list_projects` before first use. Index only when the
   repository is absent or after a named large external update.
3. Orient with `codebase-memory_get_architecture`; request only needed aspects.
4. Find definitions with `codebase-memory_search_graph`. Use natural-language,
   regex-name, or semantic search; narrow before paginating `has_more` results.
5. Trace callers, callees, data flow, or cross-service paths with
   `codebase-memory_trace_path`; follow its cursor until the bounded question is
   answered.
6. Read an exact symbol with `codebase-memory_get_code_snippet` only after
   resolving its qualified name. Use `codebase-memory_search_code` for literals.
7. Before negative or exhaustive claims, call
   `codebase-memory_check_index_coverage` for cited paths/scopes. Fall back to
   JetBrains search or direct source for skipped and partially parsed ranges.
8. Before editing, use `codebase-memory_detect_changes` or a bounded graph trace
   to identify blast radius. After editing, trust source, IDE diagnostics, and
   behavioral checks over stale graph output.

## Inspiration Repositories

Use one indexed project per question. Record project name, root path, branch or
commit, license, exact graph call, and coverage caveats. Compare reference and
active-project capabilities, then choose `adopt`, `adapt`, or `omit` with a
reason. Do not clone or re-index another repository after the evidence gap is
closed.

## Boundaries

- Never call `codebase-memory_delete_project` without explicit user approval.
- Do not write ADRs or ingest traces unless the task explicitly requests it.
- Coverage metadata is best-effort, never proof of completeness.
- Check truncation fields and paginate; do not treat the first page as complete.

<skill_result>
  <skill>codebase-memory</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Bounded graph calls, exact source confirmation, and coverage checks</evidence>
  <artifacts>Architecture map, trace, blast-radius report, or capability matrix</artifacts>
  <risks>Stale index, partial coverage, truncated graph, or none</risks>
</skill_result>
