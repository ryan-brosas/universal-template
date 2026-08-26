---
name: codegraph-context
description: "Use when navigating, searching, tracing callers/callees, analyzing complexity, or simulating blast radius in a locally-indexed repository through the codegraphcontext MCP graph."
disable-model-invocation: true
---

# CodeGraph Context

Use the `codegraphcontext` MCP to navigate and analyze a local FalkorDB code graph.
The graph is a structural index — confirm exact code in the source file before editing or making exhaustive claims.

## Workflow

1. **Orient.** Call `codegraphcontext_list_graphs` then `codegraphcontext_list_indexed_repositories` to confirm the repo is indexed. If not, call `codegraphcontext_add_code_to_graph` with the repo path; monitor with `codegraphcontext_check_job_status`.
2. **Locate.** Use `codegraphcontext_find_code` as the primary search tool — keyword, class name, or function name. Enable `fuzzy_search` only when exact match fails. Supply `repo_path` to restrict scope.
3. **Analyze.** Use `codegraphcontext_analyze_code_relationships` after locating a target:
   - `find_callers` / `find_all_callers` — who calls this function (with depth)
   - `find_callees` / `find_all_callees` — what this function calls
   - `call_chain` — direct path between two functions (`start->end`)
   - `class_hierarchy` / `overrides` — inheritance and method override graph
   - `find_importers` — what files import a module
   - `dead_code` — unused functions
   - `find_complexity` — cyclomatic complexity per function
4. **Blast radius.** Before editing, use `codegraphcontext_simulate_architectural_change` with `remove_dependency` or `remove_node` mutations to preview impact without touching the graph. Use `codegraphcontext_simulate_metrics` for coupling/cohesion/circular-dependency metrics.
5. **Quality sweep.** Use `codegraphcontext_find_dead_code` and `codegraphcontext_calculate_cyclomatic_complexity` for targeted cleanup passes.
6. **Cypher fallback.** Use `codegraphcontext_execute_cypher_query` only when the above tools cannot answer a complex multi-hop query. Use the schema below — do not guess property names.

## Graph Schema (for Cypher)

**Nodes:** `Repository` (`name`, `path`), `File` (`name`, `path`, `relative_path`), `Function` (`name`, `path`, `line_number`, `end_line`, `cyclomatic_complexity`, `source`), `Class` (`name`, `path`, `line_number`, `bases`, `source`)
**Relationships:** `CONTAINS` (Repo→File, File→Function/Class), `CALLS` (Function→Function), `IMPORTS` (File→Module), `INHERITS` (Class→Class)
**Note:** Use `path`, not `file_path`; `line_number`, not `line`.

## Boundaries

- Never call `codegraphcontext_delete_repository` without explicit user approval.
- Prefer `find_code` + `analyze_code_relationships` over Cypher — standard tools are safer and paginated.
- Graph output is structural, not semantic — verify behavior in source before shipping.
- Watch files with `codegraphcontext_watch_directory` only when the user wants live auto-reindex.

<skill_result>
  <skill>codegraph-context</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>Graph calls with repo, query type, and source confirmation for key claims</evidence>
  <artifacts>Caller tree, call chain, blast-radius simulation, complexity report, or dead-code list</artifacts>
  <risks>Stale index (re-index needed), partial coverage, unresolved job — confirm with check_job_status</risks>
</skill_result>
