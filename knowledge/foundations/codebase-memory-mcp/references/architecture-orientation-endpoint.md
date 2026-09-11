<!-- capsule-v2 -->
# get_architecture — how do you summarize a whole repo graph in one bounded call?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the architecture tool return, and how do agents use it before deep queries?

## Project-scoped stats + subsystem rollup + top symbols
**Path/Symbol:** `src/store/store.c:cbm_store_get_architecture` (~7300s) + tests/test_store_arch.c:381–420 (`store_get_architecture`, 421+ `get_architecture_project_scope`).
**Signature:** `int cbm_store_get_architecture(cbm_store_t *s, const char *project, cbm_architecture_t **out);`
**Data Shape:** Returns per-project: node/edge counts by type, language breakdown, directory-level structure rollup (top-N), and hub symbols by degree — all bounded so the response stays agent-sized; project scoping prevents cross-project bleed.

### Decisive source
```c
TEST(store_get_architecture) { ... }
TEST(get_architecture_project_scope) { ... }   /* isolation between projects */
```

**Flow:** resolve project → aggregate counts via grouped SELECTs → build tree → cap lists → emit. Agents call this FIRST to orient (which subsystems exist, where the hubs are) before issuing targeted search_graph/trace_path calls.
**Invariant:** Every list must be capped — unbounded rollups reintroduce the context-bomb class the snippet guard solves.
**Probe:** the two named tests; TOON emission twin covered by compact_out tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_get_architecture", limit: 5 });
```

## Verdict
Adopt capped aggregate-first orientation endpoints for graph APIs; adapt rollup dimensions; keep strict project scoping.
