<!-- capsule-v2 -->
# Louvain community detection — how do you cluster a code graph into modules without external libraries?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What pure-C Louvain/Leiden implementation powers the clusters aspect, and what edge cases are pinned?

## Modularity-greedy Louvain + Leiden refinement with resolution knob
**Path/Symbol:** `src/store/store.c` (louvain/leiden section, ~8400s) + tests/test_store_arch.c:928–1230.
**Signature:** `int cbm_louvain(const int64_t *nodes, int node_count, const cbm_louvain_edge_t *edges, int edge_count, cbm_louvain_result_t **out, int *out_count);`
**Data Shape:** Input: node-id array + undirected edge pairs; output per-node community id. Pinned behaviors: triangle+pair fixture separates communities correctly; empty input ⇒ OK/0; single node ⇒ own community; iteration converges (louvain_converges); Leiden variant collapses noise nodes and resolution parameter controls granularity.

### Decisive source
```c
/* Triangle should be same community */
ASSERT_EQ(comm[1], comm[2]);
ASSERT_EQ(comm[2], comm[3]);
/* Pair should be same community */
ASSERT_EQ(comm[4], comm[5]);
/* Triangle and pair different */
ASSERT_TRUE(comm[1] != comm[4]);
```

**Flow:** build adjacency → phase 1 local modularity moves → phase 2 community aggregation → repeat until stable → optional Leiden refinement pass with resolution γ for finer/coarser splits → feed `arch_clusters` aspect.
**Invariant:** Deterministic tie-breaking (input order) keeps clusters stable across runs — required because the architecture tool surfaces them to agents comparing sessions.
**Probe:** `tests/test_store_arch.c:louvain_basic`, `louvain_empty`, `louvain_single_node`, `louvain_converges`, `leiden_multilevel_collapses_noise`, `leiden_resolution_controls_granularity`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_louvain", limit: 5 });
```

## Verdict
Adopt embedded modularity clustering when you need module suggestions from call data; adapt resolution default; keep determinism guarantees for agent-facing output.
