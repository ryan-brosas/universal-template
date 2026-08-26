<!-- capsule-v2 -->
# RouteSpecificitySorter — how are routes ordered so static paths beat params without changing declaration ties?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the stable total order over route patterns, and why must ties fall back to declaration index?

## sort / comparePathSpecificity / SEGMENT_KIND_RANK
**Path/Symbol:** `packages/core/router/route-specificity-sorter.ts:sort` (:33-49), `comparePathSpecificity` (:51-79), `SEGMENT_KIND_RANK` (:18-26).
**Signature:** `static sort(routes: ResolvedRoute[]): ResolvedRoute[]`; ranks `literal:0 < param:1 < wildcard:2 < missing:3`.
**Data Shape:** Consumes `route.path` strings already normalized to the adapter's wildcard syntax; tokenizes via `RouteConflictDetector.tokenizePath` (shared tokenizer — one grammar for sorting AND conflict detection).

### Decisive source
```ts
const decoratedRoutes = routes.map((route, declarationIndex) => ({ route, declarationIndex }));
decoratedRoutes.sort((left, right) => {
  const specificityDelta = comparePathSpecificity(left.route.path, right.route.path);
  if (specificityDelta !== 0) return specificityDelta;
  return left.declarationIndex - right.declarationIndex;   // STABLE tie-break
});
// per-position compare — FIRST differing segment decides:
Array.from({ length: longestPathLength }).forEach((_, i) => {
  if (specificityDelta !== 0) return;
  const leftKind  = leftSegments[i]?.kind  ?? 'missing';
  const rightKind = rightSegments[i]?.kind ?? 'missing';
  if (leftRank !== rightRank) specificityDelta = leftRank - rightRank;
});
```

**Flow:** decorate with original index → lexicographic-by-kind comparison segment by segment → earliest position with different kinds wins the comparison → equal-specificity routes keep registration order.
**Invariant:** (1) `missing` is deliberately the LEAST specific rank — a shorter path loses against a longer one at the first absent slot (`/users` vs `/users/x`), which prevents short prefixes from shadowing longer siblings when the adapter matches by registration order. (2) Sorting is performed on a DECORATED copy and returns the same route object references — input array never mutated; identity is required by `filterSortResolvedShadows`, which maps winners back through a `Map` keyed on route objects. (3) The sort is only meaningful because registration order = match priority on Express/Fastify; more-specific-first is what makes shadows benign.
**Probe:** `packages/core/test/router/route-specificity-sorter.spec.ts` — literal<param<wildcard triple :63, declaration-order tie :81, missing-slot decision :127, no-mutation :136, same-reference return :146.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouteSpecificitySorter sort comparePathSpecificity SEGMENT_KIND_RANK", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt kind-rank + first-difference + declaration-index tiebreak as THE stable route ordering; adapt token kinds to your pattern grammar but keep `missing` lowest; omit nothing. Porting wrong: Array.prototype.sort without the decorated index (V8 stability saves you today, but the explicit tiebreak documents intent and survives engine swaps), or ranking shorter paths as MORE specific.
