<!-- capsule-v2 -->
# Conductance CSR builder — how do directed-ish typed edges become one symmetric diffusion operator?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** The graph has seven typed edge kinds (contains/imports/invokes/inherits/tests/join/anchors), some semantically directed, with parallel edges between the same pair — what single rule turns that into the weighted undirected adjacency diffusion needs, without letting duplicate pairs double-conduct?

## Max-conductance undirected CSR with degrees
**Path/Symbol:** `src/core/heat.ts:buildCsr` (:36-65); edge model `src/core/types.ts:EdgeKind` (:17-25); consumer `src/core/ops.ts:assembleState` adjacency mirror (:158-167).
**Signature:** `buildCsr(g: Graph): Csr` where `Csr = { n, rowPtr: Uint32Array, col: Uint32Array, w: Float64Array, deg: Float64Array }`.
**Data Shape:** Input edges `{a, b, kind, w}` (w ≥ 0 conductance). Output is standard CSR plus `deg[i]` = sum of incident weights (the degree used as D^{-1/2} and reused by ops as the node's "conductance" score).

### Decisive source
```ts
export const buildCsr = (g: Graph): Csr => {
  const n = g.nodes.length;
  const best = new Map<string, number>();
  for (const e of g.edges) {
    if (e.a === e.b) continue;                       // no self loops
    const key = e.a < e.b ? `${e.a}|${e.b}` : `${e.b}|${e.a}`;  // order-independent key
    best.set(key, Math.max(best.get(key) ?? 0, e.w));  // MAX, not SUM
  }
  // ... counting sort into rowPtr/col/w, each pair written BOTH directions,
  const deg = new Float64Array(n);
  for (const [a, b, ew] of pairs) { deg[a]! += ew; deg[b]! += ew; }
  return { n, rowPtr, col, w, deg };
};
```
```ts
// applyNegP — isolated nodes map to themselves under heat (no NaN):
for (let i = 0; i < n; i++) invSqrt[i] = deg[i]! > 0 ? 1 / Math.sqrt(deg[i]!) : 0;
```

**Flow:** dedupe unordered pairs keeping the max weight → counting-sort into CSR → symmetrize both directions → accumulate degrees. Ops separately mirrors the FULL multigraph into an `adjacency` map (all kinds preserved, pre-sorted contains-last/weight-desc/node-id) for reason walks and basins — the CSR is only the diffusion operator; typed evidence lives in the adjacency mirror.
**Invariant:** Parallel same-pair edges collapse by MAX (never SUM) — otherwise a route joined by both a literal and a co-change would double its conductance and skew D^{-1/2}. Isolated nodes (deg 0) get invSqrt 0 so they are fixed points of the field instead of NaN sources. Self-loops are dropped before keying.
**Probe:** `tests/heat.test.ts` — randomGraph suites exercise buildCsr through heatAt positivity/monotonicity ("heat fields are non-negative and the seed stays hottest at small t"); `tests/render.test.ts` fan-graph fixtures build CSR from invoke-only graphs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "buildCsr csr degree", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the max-conductance symmetrization + degree array as the universal bridge from heterogeneous typed edges to spectral operators, and the zero-degree guard. Adapt edge-kind set and weights to your extractor. Omit nothing — this is ~30 lines with two non-obvious traps (MAX-not-SUM, deg-0 guard) a porter will otherwise get wrong.
