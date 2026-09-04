<!-- capsule-v2 -->
# Deterministic resolved call graph (extractCallees → weight-split edges → PageRank/in-degree) — how are calls resolved without type information, and why must graph signals be additive?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How do you build a useful call graph from text outlines alone, with ambiguous names?

## Name-resolution with weight splitting across candidates
**Path/Symbol:** `src/codegraph.zig` whole-file (`extractCallees` :62–107, `buildEdges` :112–134, `inDegreeCentrality` :139–146, `pageRank` :151–199, `shortestCallPath` :229–308); builder `Explorer.ensureCallGraph` :5544–5729.
**Signature:** `Edge{from,to,weight}` with `w = 1.0 / cands.len` — a cleanly-resolved name contributes full weight, an ambiguous one is discounted across its definitions; self-edges dropped unless allowed.
**Data Shape:** Nodes = function/method symbols from outlines (id = insertion order); `FuncInput{id, body}` sliced from content via outline line ranges; resolve map = name → []NodeId from symbol_index. Adjacency built forward (`adj`) AND reverse (`radj` — prebuilt ONCE; rebuilding per query was ~43% of an uncached ranked search).

### Decisive source
```zig
// Skip line comments, block comments, and string/char literals so an identifier
// mentioned only inside one is not mistaken for a call site (#548 family).
if (c != '(') continue;
var end = i;
while (end > 0 and (body[end - 1] == ' ' or body[end - 1] == '\t')) end -= 1;
var start = end;
while (start > 0 and isIdentChar(body[start - 1])) start -= 1;
if (!isIdentStart(name[0])) continue;   // started on a digit → not an ident
if (isCallKeyword(name)) continue;      // if/for/while/return/... cross-language superset
```
PageRank details: damping 0.85, 20 iterations, dangling nodes redistribute their rank uniformly (`share = damping * dangling / n_nodes` added to every scratch slot each iteration). Env `CODEDB_IN_DEGREE_CENTRALITY` swaps PageRank for weighted in-degree ("god node" signal).

**Flow:** outlines give functions+bodies → extract deduped `ident(` callees (comment/string-aware) → resolve each name through symbol_index → append weight-split edges → adjacency + reverse adjacency + per-node scores aggregated PER-PATH into `call_centrality` (sum of node scores per file) → `centralityBoost = 1 + 0.15·ln(1+c)` folds into ranking. `findCallPath` = level-tracked BFS with parent reconstruction, max_hops guard, early exit when from∩to.
**Invariant:** THE GRAPH IS NEVER A FILTER — misresolved edges may only add boost (see rerank capsule). `ensureCallGraph` refuses to build from a DEFERRED symbol index (#564): an empty graph would be cached forever; callers ensureSymbolIndex first, ranking paths just skip the boost until built. Lazy builds bump search_gen so caches invalidate at the moment the signal appears.
**Probe:** `src/test_explore.zig` :52 "codegraph: buildEdges resolves callees + inDegree centrality", "codegraph: extractCallees finds calls, filters keywords", "audit: extractCallees ignores comment/string mentions", "codegraph: pageRank ranks highly-called nodes above leaves", "codegraph: shortestCallPath finds A→helper→B chain".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", query: "extractCallees buildEdges pageRank", limit: 10 });
```

## Verdict
Adopt text-level callee extraction with comment/string skipping and weight-split ambiguity handling; adapt the keyword superset to your languages (over-filtering only costs a little boost); omit LLM/community phases — the deterministic core is the portable part.
