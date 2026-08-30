<!-- capsule-v2 -->
# CodePath public surface + safe traversal — how do rules walk a finished code path without infinite-looping on cycles, and what do skip/break mean?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** What is the read-side API of a completed code path and what must a traversal respect to terminate on loopy graphs?

## CodePath + traverseSegments
**Path/Symbol:** `lib/linter/code-path-analysis/code-path.js:CodePath` (:22–332) — constructor (:31–67), getters `initialSegment/finalSegments/returnedSegments/thrownSegments` (:84–124), `traverseSegments(optionsOrCallback, callback)` (:148–331).
**Signature:** `codePath.traverseSegments({first?, last?}?, (segment, controller) => void)`; `controller.skip()` abandons the current branch's continuation; `controller.break()` halts everything.
**Data Shape:** `origin` ∈ "program"|"function"|"class-field-initializer"|"class-static-block"; `upper`/`childCodePaths` form the function-nesting tree (children registered at construction); `finalSegments = returnedForkContext ∪ thrownForkContext` (dedup via addToReturnedOrThrown) — all reachable by construction.

### Decisive source
```js
while (stack.length > 0) {
  record = stack.at(-1); segment = record[0]; index = record[1];
  if (index === 0) {
    if (visited.has(segment)) { stack.pop(); continue; }
    // determinstic order: visit only when ALL prevs are visited —
    // looped prevs count as visited so back-edges never stall or re-enter:
    if (segment !== startSegment && segment.prevSegments.length > 0 &&
        !segment.prevSegments.every(isVisited)) { stack.pop(); continue; }
    visited.add(segment);
    const shouldSkip = skipped.size > 0 && segment.prevSegments.length > 0 &&
                       segment.prevSegments.every(isSkipped);
    if (!shouldSkip) {
      resolvedCallback.call(this, segment, controller);
      if (segment === lastSegment) controller.skip();
      if (broken) break;
    } else skipped.add(segment);
  }
  // manual stack with per-record next-index → resumable DFS without recursion
}
```

**Flow:** explicit `[segment, nextIndex]` stack walks `nextSegments` depth-first from `first||initialSegment`; a segment is delivered only after every reachable predecessor was delivered, which yields source order for acyclic regions and exactly-once delivery around loops.
**Invariant:** `isVisited/isSkipped` both OR-in `isLoopedPrevSegment` — loop back-edges are treated as satisfied predecessors; skipping propagates only when ALL predecessors were skipped; `last` is enforced by auto-skipping past it, not by graph surgery. Rules may store per-segment data keyed by `segment.id` (that's why ids exist).
**Probe:** `tests/lib/linter/code-path-analysis/code-path.js` (:126–302 ordered-traverse fixtures simple/if/switch/while/for/for-in/try-catch; :304 first→last window; :334/:369/:404/:444 controller.break/skip semantics incl. top-segment skip).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "CodePath traverseSegments controller skip finalSegments childCodePaths", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.code-path-analysis.code-path.CodePath.traverseSegments" });
```

## Verdict
Adopt all-prevs-visited ordering + looped-prev-as-visited + resumable-stack traversal as the safe read API for any CFG you expose; adapt the controller vocabulary; omit origin strings that your language cannot produce.
