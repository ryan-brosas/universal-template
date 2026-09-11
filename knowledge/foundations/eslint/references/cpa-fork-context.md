<!-- capsule-v2 -->
# CPA fork-context algebra — how do you track N parallel execution lanes and merge them back without losing segment alignment?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you represent "the code may continue from any of these points" as data, and what breaks if you flatten or mis-merge it?

## ForkContext
**Path/Symbol:** `lib/linter/code-path-analysis/fork-context.js:ForkContext` (:164–372) + helpers `createSegments` (:56–94), `mergeExtraSegments` (:104–155).
**Signature:** `new ForkContext(idGenerator, upper, count)`; statics `newRoot(id)`, `newEmpty(parent, shouldForkLeavingPath)`; methods `makeNext/makeUnreachable/makeDisconnected(startIndex,endIndex)`, `add(segments)`, `replaceHead(segments)`, `addAll(other)`, `clear()`.
**Data Shape:** `segmentsList: Array<Array<CodePathSegment>>` — every row has exactly `count` columns; column i is one logical lane. `count` is 1 normally, ×2 per enclosing `finally` (parallel normal/leaving paths), so nested finallys give 4, 8… `head` = last row; negative start/end indices are relative to the list end (`makeNext(0,-1)` = "append after all rows", `makeNext(-1,-1)` = "append after head only").

### Decisive source
```js
// add(): a wider incoming array is merged pairwise down to `count` columns —
// inside finally, [normal..., leaving...] halves repeatedly until it fits.
add(segments) {
  assert(segments.length >= this.count, `${segments.length} >= ${this.count}`);
  this.segmentsList.push(mergeExtraSegments(this, segments));
}
static newEmpty(parentContext, shouldForkLeavingPath) {
  return new ForkContext(parentContext.idGenerator, parentContext,
    (shouldForkLeavingPath ? 2 : 1) * parentContext.count);
}
```

**Flow:** `forkPath()` adds a fresh segment after the parent context's last row; `forkBypassPath()` re-adds the parent's head unchanged (the "no else branch" path); `replaceHead` swaps only the last row; `popForkContext` on the state pushes the child's final row into the parent via `replaceHead(lastContext.makeNext(0,-1))`.
**Invariant:** never store segments as a flat set — lane alignment by column index is load-bearing everywhere (finally's half-split in `popTryContext`, `makeLooped` pairing, `makeFinallyBlock`'s per-column leaving-segment synthesis); `assert(length >= count)` guards it. Reachability of a context = `head.some(reachable)` and an empty head is NOT reachable.
**Probe:** `tests/lib/linter/code-path-analysis/fork-context.js` (:332 add throws `/0 >= 1/`; :349 merge-extra; :376–405 replaceHead-only-modifies-head; :128 double count when `shouldForkLeavingPath`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "ForkContext makeNext replaceHead mergeExtraSegments", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.code-path-analysis.fork-context.ForkContext.add" });
```

## Verdict
Adopt the row×column lane matrix with count-doubling for parallel leave-paths and the negative-index range vocabulary; adapt the assert style to your host; omit the finally-specific merging only if your language has no abrupt-exit-with-cleanup construct.
