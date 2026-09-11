---
title: codebase-memory
summary: Use when navigating, indexing, tracing, or comparing repositories via the Codebase Memory graph — default gather path is query CBM before broad ripgrep/find walks.
kind: playbook
---

# Codebase Memory

Codebase Memory is a persistent operational index over explicitly indexed
repositories: a rebuildable projection of source, safe to recreate from its
canonical repositories. It is not historical experience memory and not
authority for current code. Direct source (and IDE diagnostics) own truth:
confirm exact code before editing or making exhaustive claims.

This playbook loads on demand through research-pack. Activate the `code-graph`
MCP profile when using the graph. Cold MCP schemas are dynamic cost, not hot
startup metadata. For stack-pattern capsules outside this index, start at
`skills/foundation-pack/SKILL.md` (one category, one foundation, one capsule).
Lane map: `knowledge/playbooks/evidence-router/README.md`.

## Core Principle

**Default gather path for most models:** query Codebase Memory before a broad
filesystem walk (ripgrep/find across large trees). The graph is a derived
projection — evidence, not authority — and must be confirmed against current
source and tests before edits or exhaustive claims.

## Default gather path (before broad walk)

Use this order unless Fovea already answered an active working-set question,
or the user forbade MCP:

1. Connect `codebase-memory` and call `codebase-memory_list_projects`.
2. If the repo is indexed: `get_architecture` (needed aspects only) →
   `search_graph` / `trace_path` (narrow, paginate `has_more`) →
   `get_code_snippet` / `search_code` for the exact target.
3. `check_index_coverage` before negative or exhaustive claims; fall back to
   IDE/direct source for skipped or partial ranges.
4. Broad ripgrep/find **only** for gaps the graph cannot close, or after
   coverage says the path is out of index.
5. If the repo is **not** in `list_projects`: use Fovea (when available) or
   direct source. Do **not** create an index unless the user explicitly asks.

Fovea remains the preferred **active working-set** map when it is available and
sufficient. CBM is the default **before sprawling search**, especially across
services, inspiration repos, or hosts without Fovea.

## When to Use / NOT

- **Use when:** navigating, locating symbols/patterns, tracing callers/callees,
  comparing indexed inspiration repos, or any gather that would otherwise start
  with a broad tree walk.
- **NOT when:** a named file/symbol path is already known and direct read is
  enough; or the user explicitly wants filesystem-only search. Do not index a
  current/active owned project merely because the MCP is connected. Index
  creation requires an explicit user request. Never call
  `codebase-memory_delete_project` without explicit user approval. Do not write
  ADRs or ingest traces unless requested.

## Workflow

1. Connect to the `codebase-memory` MCP and read its server instructions.
2. `codebase-memory_list_projects` before first use. Absent project → Fovea or
   direct source unless the user requests index creation. Re-index an existing
   library entry only after a named large external update or explicit request.
3. `codebase-memory_get_architecture` — only needed aspects.
4. `codebase-memory_search_graph` — natural-language, regex-name, or semantic;
   narrow before paginating `has_more`.
5. `codebase-memory_trace_path` for callers, callees, data flow, cross-service
   paths; follow cursor until the bounded question is answered.
6. `codebase-memory_get_code_snippet` after a qualified name;
   `codebase-memory_search_code` for literals.
7. Before negative/exhaustive claims: `codebase-memory_check_index_coverage`
   for cited paths/scopes; JetBrains/direct source for skipped/partial ranges.
8. Before editing: `codebase-memory_detect_changes` or a bounded graph trace for
   blast radius. After editing, trust source, IDE diagnostics, and behavioral
   checks over stale graph output.

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
- Cache location is machine-local (`CBM_CACHE_DIR` / host config); do not hard-code paths into skills.
- Porting CBM internals belongs in `codebase-memory-mcp-foundation`, not here.

## Red Flags

- Broad ripgrep/find as the first gather step when CBM is available.
- Treating the graph as source of truth.
- Calling `codebase-memory_delete_project` without approval.
- Treating the first page as complete (truncation fields unchecked).
- Graph-based negative or exhaustive claims without `check_index_coverage`.
- Cloning or re-indexing after the evidence gap is closed.
- Automatically indexing an active or newly completed owned project.

## Verification

Exact source confirmation before editing; coverage checked before graph-based
negative/exhaustive claims; blast radius identified before editing; after
editing, trust source/IDE/behavior over stale graph output.

## References

- Lane choice: `knowledge/playbooks/evidence-router/README.md`
- Capsule discovery: `skills/foundation-pack/SKILL.md` → `knowledge/foundations/`
- CBM internals (porting only): `knowledge/foundations/codebase-memory-mcp/README.md`
- MCP registry/profile: `mcp/servers.json`, `mcp/profiles.json`, `mcp/catalog.md`
