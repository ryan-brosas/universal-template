<!-- capsule-v2 -->
# Transitive loop depth — how do you estimate interprocedural nesting (and flag recursion) without proving big-O?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you propagate per-function loop_depth along CALLS edges into a worst-case transitive metric with cycle safety?

## Memoized DFS: tld = own + max(callee tld), back-edge ⇒ recursive
**Path/Symbol:** `src/pipeline/pass_complexity.c:tld_dfs` (104–138) + module header contract (1–29).
**Signature:** `static int tld_dfs(const cbm_gbuf_t *gb, int64_t id, const int *loop_depth, int *tld, char *state, bool *recursive, int64_t maxid, int depth);` — `CBM_TLD_MAX_DEPTH 256`.
**Data Shape:** Writes two node properties on every Function/Method: `transitive_loop_depth` (int) and `recursive` (bool). State machine per node: 0 unvisited / 1 in-progress / 2 done.

### Decisive source
```c
/* Memoized DFS: tld(id) = loop_depth(id) + max over CALLS-callees of tld(callee).
 * state: 0=unvisited, 1=in-progress (back-edge → cycle), 2=done. */
if (state[id] == 1) { recursive[id] = true; return 0; }   /* call-graph cycle */
...
/* The estimate assumes calls may occur inside loops (an upper bound) — it is a
 * queryable bottleneck *candidate* signal, not a proof ... Cycles are broken
 * and flagged via a `recursive` property. */
```

**Flow:** seed loop_depth from Tier-A extraction properties → DFS over CALLS out-edges computing own-depth + best callee depth → in-progress re-entry marks the node recursive and contributes 0 (breaking the cycle) → write-back merges the two properties into the existing JSON object.
**Invariant:** Cycle handling must not recurse forever AND must not silently drop the flag; depth cap guards hostile graphs; the metric is an UPPER BOUND candidate signal by construction.
**Probe:** `tests/test_pipeline.c:pipeline_complexity_transitive_loop_depth` (inner tld=2; outer = 1+inner = 3 interprocedurally; self-recursive fn gets `recursive:true`); consumers query `coalesce(f.transitive_loop_depth,0)` in tests/test_cypher.c:1219+.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "tld_dfs", limit: 5 });
```

## Verdict
Adopt memoized state-machine propagation for any graph-derived metric; adapt the property names/JSON merge to your store; omit cognitive-complexity tiering if you only need the bottleneck candidate.
