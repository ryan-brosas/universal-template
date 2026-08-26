<!-- capsule-v2 -->
# Edge property merge — how can parallel workers dedup edges without thread-scheduling deciding the winner?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When two strategies (LSP vs textual registry) mint the same logical CALLS edge, which properties survive — deterministically?

## Commutative confidence total order
**Path/Symbol:** `src/graph_buffer/graph_buffer.c:edge_props_should_replace` (1068–1081) + `make_edge_key` (179–198).
**Signature:** `static bool edge_props_should_replace(const char *existing_json, const char *incoming_json);` / `int64_t cbm_gbuf_insert_edge(gbuf, source_id, target_id, type, properties_json);`
**Data Shape:** Edge dedup key = `"srcID:tgtID:type"` (+ `local_name` slice for IMPORTS). Properties are JSON blobs carrying optional `"confidence"`/`"strategy"`/`"via"`. Absent/unparseable confidence reads as −1 so any confident edge outranks a bare one.

### Decisive source
```c
/* This rule is a total order over the two candidates, hence commutative and
 * associative — the outcome is independent of arrival order:
 *   1. higher "confidence" wins ...
 *   2. on equal confidence, the lexicographically greater blob wins ... */
if (!incoming_json || strcmp(incoming_json, "{}") == 0) return false; /* never displace */
double inc = edge_props_confidence(incoming_json);
double cur = edge_props_confidence(existing_json);
if (inc != cur) return inc > cur;
return strcmp(incoming_json, existing_json) > 0;
```

**Flow:** insert computes composite key → hash hit ⇒ apply should_replace → winner's blob stored, id returned unchanged → miss ⇒ append new edge + index it. IMPORTS keys add the local_name so `import {A,B}` yields TWO edges; over-long names re-key with FNV-1a of the FULL name prefixed by 0x01 (cannot collide with verbatim keys).
**Invariant:** The merge must stay commutative+associative — per-worker buffers merge in worker-slot order, so ANY arrival-order rule makes surviving attributes a function of thread scheduling. An empty incoming blob never displaces real properties.
**Probe:** `tests/test_graph_buffer.c:gbuf_edge_props_merge_is_order_independent`, `gbuf_edge_props_merge_prefers_higher_confidence`, `gbuf_edge_props_merge_keeps_existing_on_empty`; end-to-end by `tests/test_pipeline.c:pipeline_imports_multi_symbol_edges` and writer-side `tests/test_sqlite_writer.c:sw_imports_local_name_unique`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "edge_props_should_replace", limit: 5 });
```

## Verdict
Adopt the commutative merge law for any concurrently-fed dedup map; adapt key composition to your edge schema; omit the 0x01 hash-key escape if your names are length-bounded.
