<!-- capsule-v2 -->
# Edge strategy classification — how do you tell an agent HOW an edge was resolved (and therefore how much to trust it)?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the closed strategy→class vocabulary for trace evidence, and what must NEVER be silently dropped?

## Closed-vocabulary mapping: lsp / language_rule / heuristic / unresolved
**Path/Symbol:** `src/mcp/mcp.c:cbm_mcp_edge_strategy_class` + tests/test_mcp.c:3303 (`trace_evidence_strategy_class_vocabulary_is_closed`), 3353 (`tool_trace_path_evidence_is_opt_in_and_class_mapped`).
**Signature:** `const char *cbm_mcp_edge_strategy_class(const char *strategy);`
**Data Shape:** lsp* (12 strategies incl. virtual_dispatch, smart_ptr_dispatch) → "lsp"; php_/perl_ static/typed rules → "language_rule"; callee_suffix, field_type_hint, service_pattern, fastapi_depends → "heuristic"; "lsp_unresolved"/unknown → "unresolved"; ONLY NULL/empty ⇒ unclassified.

### Decisive source
```c
/* A failed LSP resolution is reported as unresolved, not as "lsp" — the
 * caller's question is whether the edge is trustworthy, and "we tried LSP
 * and it did not resolve" answers no. */
ASSERT_STR_EQ(cbm_mcp_edge_strategy_class("lsp_unresolved"), "unresolved");
/* Only a NULL/empty strategy is unclassified — an unmapped non-empty value
 * must never silently disappear from the output. */
```

**Flow:** edges carry per-edge strategy strings from extraction passes → trace evidence (opt-in) maps each to a trust class → unknown non-empty values surface as unresolved rather than vanishing.
**Invariant:** Closed vocabulary with fail-loud fallback: adding a new pass REQUIRES extending the map (test sweeps every literal in src/+internal/); trust classes are ordinal, not scores.
**Probe:** the two named tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "edge_strategy_class", limit: 5 });
```

## Verdict
Adopt closed strategy vocabularies with sweep-tests over all literals; adapt class names; never let unmapped values vanish — that's silent data loss.
