<!-- capsule-v2 -->
# Impact cascade — how do you rank review order for a change with causal reasons per warmed node?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Given changed files (or a PR base), what warms, in what order, labeled with WHICH evidence channel — and what structured payload does a downstream verdict gate need?

## Seed-file diffusion + BFS reason walk + node-keyed verdict payload
**Path/Symbol:** `src/core/ops.ts:impact/reasonFor/warmedNodes assembly` (:906-1146).
**Signature:** `impact(root, {files?, symbols?, includeUncommitted?, base?, budget?}, ensured?): Promise<OpResult>`; diffusion at fixed t=4; seeds = first node of each changed file (+ resolved symbols, + `git diff base...HEAD` names when base given).
**Data Shape:** details payload: `warmedAnchors[]`, `warmedFiles[]`, `warmedMass: Record<file, Σheat>` (seeds excluded), `seedMass` (graph-size-invariant normalizer), `warmedReasons: Record<file, string[]>`, `warmedNodes: Record<"kind|name@file", {file, m, r}>` capped at top 2000 by mass, `historyPartners`.

### Decisive source
```ts
// Verdict-grade warmth, keyed by stable node identity ("kind|name@file") so
// turn-sync's heat memory can age PER HUNK rather than per file: a charged
// cascade node stays silent on revisits, while a novel hunk in a known file
// still fires. File nodes are coarse duplicates of their symbols (they warm
// whenever anything nearby does) and would re-smear memory file-wide, so they
// join display aggregation but NEVER the memory ledger.
warmed.sort((a, b) => b[1].m - a[1].m);
for (const [k, v] of warmed.slice(0, 2000)) warmedNodes[k] = v;
// Per-NODE first-encounter reasons: the memory is charged at the granularity
// a node warms at, not smeared over its file. 1-hop edges inherit the channel
// directly; deeper nodes get unweighted-BFS shortest-path reason chains
// (contains hops omitted from user-facing reasons, max 3 kept).
const farNode = seedFiles.has(aFile) && !seedFiles.has(bFile) ? edge.b : ...;
noteNode(farNode, [reason]);
```

**Flow:** resolve seed set → add recency-decayed co-change partners INTO the same seed vector → diffuse once (t=4) → aggregate per-file mass excluding seeds → label channels: direct seed-adjacent edges inherit their kind's reason ("call dependency"/"import dependency"/"test dependency"/"inheritance"/"shared literal"/"shared route"); BFS explains beyond-one-hop files; history overlays stamp "co-change history"; unlabeled residue = "graph path" → render groups (anchors ⚑ first, then files by mass with top symbols) inside the shared budgeted group renderer with overflow artifact.
**Invariant:** Reasons attach at NODE granularity (the sync ledger charges per hunk); seeds' own files are excluded from the review list but their retained heat becomes `seedMass`, the scale-free denominator for comparing cascades across repos of different sizes; unknown seed files guide instead of crashing ("no seed files").
**Probe:** `tests/ops.test.ts` — "impact warms the client and spec when the Go handler file is edited" (web/api.ts + openapi.yaml + worker/search.rs warmed; reasons["web/api.ts"] contains "shared literal"; no server/users.go lines); "impact with unknown files guides instead of crashing". `tests/cochange.test.ts` overlay test pins "co-change history" labels end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "impact warmedNodes warmedMass reasonByNode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-diffusion impact with history partners folded into the seed vector, node-granular reason walks, sqrt-free per-file aggregation, and the structured warmed* payload contract that lets an external gate (sync) do verdict math without text parsing. Adapt t and reason vocabulary. Omit the bench-only token passthrough.
