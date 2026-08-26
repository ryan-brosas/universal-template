<!-- capsule-v2 -->
# Basins — how do you group features on repos that declare no routes?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** CLIs, libraries, and kernels have zero anchors — the sketch silhouette would collapse to directory buckets. How do you recover feature-sized regions from pure conductance, deterministically?

## Greedy conductance-cut growth around self-dense seeds
**Path/Symbol:** `src/core/basins.ts:detectBasins` (:20-101); activation gate `src/core/ops.ts:sketch` (:649-658: only when production anchors < 6 AND nodes ≥ 48).
**Signature:** `detectBasins(adjacency, conductance: Float64Array, n, eligible?, include?): Basin[]` where `Basin = {seed, members, mass}`; constants MAX_BASINS=12, MAX/MIN_BASIN_SIZE=64/4.
**Data Shape:** Seed score = `conductance·(0.25+0.75·tri) + deg·0.02`, requiring deg ≥ 2, conductance > 0, and triangle density ≥ 0.08 (or deg ≥ 6). Triangle density = fraction of a node's neighbor pairs that are co-neighbors, sampled over the first 12 neighbors with an O(deg²) cap.

### Decisive source
```ts
// eligible marks nodes that may SEED a basin (symbols, not files/anchors: a
// file's contains-star has ~zero triangle density and yields useless seeds).
// include optionally constrains EVERY member — production-first sketching
// without changing the underlying graph.
// Grow: repeatedly attach the boundary node with the best ratio of
// weight-into-basin to weight-total. Stop when the cut dominates.
if (best < 0 || bestRatio < 0.15) break;
members.add(best); internal += boundary.get(best) ?? 0;
const cut = [...boundary.values()].reduce((a, b) => a + b, 0);
if (cut > 2.6 * Math.max(internal, 0.001) && order.length >= MIN_BASIN_SIZE) break;
...
// A basin that swallows a third of a large graph is not a feature; it's the graph.
if (order.length > Math.max(40, n / 3)) continue;
```

**Flow:** score + rank candidate seeds → greedily grow each basin by best in-weight/total-weight ratio → stop at the 0.15 floor or when cut > 2.6× internal mass (the REAL guard; the ratio floor is deliberately permissive because small tight groups admit low first-step ratios) → discard <4-member stubs and ≥⅓-of-graph monsters → mark members claimed so basins don't overlap.
**Invariant:** Deterministic and bounded (sorted candidates, ≤12 basins, ≤64 members); seeding is symbol-only via `eligible`; scoping filters membership via `include` without mutating the shared graph; hubs are star points (near-zero triangles) so they never seed — they get claimed INTO basins instead.
**Probe:** `tests/basins.test.ts` — "separates two dense clusters joined by a weak bridge" (no cross-cluster smear: min(side-a-members, side-b-members) ≤ 1); "pure star topology yields no basin"; "eligibility filter excludes file/anchor-style nodes"; "keeps excluded nodes out of scoped region membership".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "detectBasins triScore conductance", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt triangle-density seed scoring + ratio-greedy growth + cut-domination stop + the swallow guard, and the eligible/include split for operation-scoped views. Adapt thresholds to your edge-weight distribution. Omit nothing; the module documents its own tuning rationale inline.
