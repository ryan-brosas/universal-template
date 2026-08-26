<!-- capsule-v2 -->
# SCC cycle detection — how do you find circular call dependencies as an opt-in architecture aspect?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the cycles aspect return and how is SCC computed?

## Tarjan-style SCC with size>1 filter
**Path/Symbol:** `src/store/store.c` architecture cycles aspect + tests/test_mcp.c:1883 (`tool_get_architecture_cycles_detects_scc`).
**Signature:** `get_architecture` with `aspects:["cycles"]`.
**Data Shape:** Fixture A→B→C→A plus acyclic D→E: response reports `cycles: 1` (exactly one SCC of size>1) listing cycproj.m.A/B/C members; acyclic pairs never appear.

### Decisive source
```c
/* cycle A->B->C->A, plus acyclic D->E */
... {"cycles"} ...
ASSERT_NOT_NULL(strstr(inner, "cycles: 1")); /* exactly one SCC of size>1 */
ASSERT_NOT_NULL(strstr(inner, "cycproj.m.A"));
```

**Flow:** load CALLS edges → iterative SCC computation → filter to components with >1 node (self-loops policy separate) → emit count + member lists.
**Invariant:** Size-1 SCCs are every recursive function — they must be filtered or the answer is noise; the count line format is pinned for agent parsing.
**Probe:** `tests/test_mcp.c:tool_get_architecture_cycles_detects_scc`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cycles", limit: 5 });
```

## Verdict
Adopt SCC-based cycle reporting with explicit self-loop policy; adapt emission; keep the opt-in aspect pattern for expensive analyses.
