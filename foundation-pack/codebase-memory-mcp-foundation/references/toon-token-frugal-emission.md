<!-- capsule-v2 -->
# TOON emission — how do you cut 40–60% of tool-response tokens without losing retrieval fidelity?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What tabular wire format should LLM-facing tools emit for homogeneous result sets, and what must never leak into it?

## Header-declared columns + field blocklist
**Path/Symbol:** `src/mcp/compact_out.h` (module, quoting rules 1–20) + `src/mcp/mcp.c:sg_field_blocked` (3294–3296) and TOON emitters (3012+, 3400+).
**Signature:** `void cbm_tree_table_header(cbm_sb_t *sb, const char *key, int n, const char *const *cols, int ncols);` / row_begin → cell_str/cell_int/cell_real per column → row_end.
**Data Shape:** Format: `key[n]{col1,col2,...}:` header; rows at 2-space indent. A cell is double-quoted iff empty, leading/trailing whitespace, contains comma/quote/newline/CR, or would read as a literal (true/false/null/number). JSON-style escaping; newlines become `\n`.

### Decisive source
```c
/* Tool responses are consumed by LLM agents, where every byte is context
 * tokens. TOON encodes the same data as JSON but declares tabular fields once
 * in a header and streams rows line by line, cutting 40-60% of tokens ... */
...
static bool sg_field_blocked(const char *f) {
    return strcmp(f, "fp") == 0 || strcmp(f, "sp") == 0 || strcmp(f, "bt") == 0;
}
```

**Flow:** handler buffers rows first (the table header carries column names so the count must be known) → emit scalar lines via `cbm_tree_scalar_*` or a table via header+rows → internal similarity/semantic intermediates (`fp` minhash hex, `sp` structural profile, `bt` body tokens — ~45% of legacy payload) are BLOCKLISTED from output even when explicitly requested via `fields`; core-column requests are dropped with an explanatory hint instead of emitting silent empty columns.
**Invariant:** The blocklist applies to BOTH default and explicit-field paths; requesting a core column as extra must teach, not silently no-op.
**Probe:** `tests/test_mcp.c:tool_search_graph_toon_never_leaks_internal_fields` (sentinel values absent even when requested; non-blocked field still emitted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "emit_search_results_toon", limit: 5 });
```

## Verdict
Adopt header-once tabular emission with a hard internal-field blocklist for any LLM-consumed API; adapt quoting to your format spec (toonformat.dev); omit JSON-format twins if you have only one consumer.
