<!-- capsule-v2 -->
# TOON quoting grammar — exactly when must a cell be double-quoted?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What minimal quoting rule keeps tabular rows unambiguous for LLM consumers?

## Quote iff empty / edge-whitespace / delimiter / literal-lookalike
**Path/Symbol:** `src/mcp/compact_out.h:1–20`.
**Signature:** cell emitters `cbm_tree_cell_str/cell_int/cell_real(sb, val, first)`.
**Data Shape:** A cell/scalar is double-quoted IFF it is empty, has leading or trailing whitespace, contains a comma, quote, newline, or CR, or would read as a non-string literal (true/false/null/number). Quotes and backslashes escape JSON-style; newlines become `\n`.

### Decisive source
```c
/* Quoting: a cell/scalar is double-quoted iff it is empty, has leading or
 * trailing whitespace, contains a comma, quote, newline, or CR, or would
 * read as a non-string literal (true/false/null/number). Quotes and
 * backslashes are escaped JSON-style; newlines become \n. */
```

**Flow:** row emission walks cells → apply predicate per cell → quote+escape when needed → emit comma-separated within the header-declared column order.
**Invariant:** Literal-lookalike quoting is load-bearing — an unquoted `true` or `007` silently changes type on reparse; the rule must be applied uniformly to scalars and cells.
**Probe:** exercised by every TOON emitter; blocklist interplay pinned in tests/test_mcp.c:2229 (`tool_search_graph_toon_never_leaks_internal_fields`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_tree_cell_str", limit: 5 });
```

## Verdict
Adopt the predicate verbatim if you emit TOON-like tables; adapt escapes; nothing here is optional once you accept the format.
