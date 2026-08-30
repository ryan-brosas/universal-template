<!-- capsule-v2 -->
# TOON/JSON format duality — how do you serve both human-compact and machine-structured output from one handler?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the contract for a `format` argument so both shapes carry the SAME data model?

## Same tree model, two serializations
**Path/Symbol:** `src/mcp/mcp.c` — `format:"json"` branches (3154, 3852, 10975) + descriptions promising parity (510: "format=\"json\" returns the SAME tree model as structured JSON", 667).
**Signature:** per-tool `char *format_arg = cbm_mcp_get_string_arg(args, "format");` dispatching between TOON table emitters and JSON-tree writers.
**Data Shape:** Both formats serialize the identical grouped/tree model; only the wire encoding differs. Unknown/absent format ⇒ default compact form; `"json"` opts into structured.

### Decisive source
```c
/* format:"json" = json-stringified tree: cols + column-ordered rows ... */
/* ... "json" returns the SAME tree model as structured JSON. */
```

**Flow:** parse args → build the tool's canonical result model once → branch at emission: TOON header+rows vs JSON stringify → identical fields/values in both; field blocklists and core-column hints apply before either writer.
**Invariant:** Divergent data models across formats is the bug class this contract kills — any new field must be added to BOTH emitters or neither.
**Probe:** tests asserting both spellings return consistent content (e.g., tests/test_mcp.c search_graph semantic-only case checks `"total":0` in JSON while TOON twin covers tables).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "format json same tree", limit: 5 });
```

## Verdict
Adopt single-model dual-emission whenever an LLM-facing API also feeds scripts; adapt format names; omit TOON if you never need token-frugal tables.
