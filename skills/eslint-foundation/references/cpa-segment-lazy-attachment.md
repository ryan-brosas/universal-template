<!-- capsule-v2 -->
# CPA segment lazy-attachment — how do segments become real graph edges only when actually walked, and why must unreachable tails survive?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you keep speculative fork segments out of the final graph while still remembering paths nobody executed?

## CodePathSegment
**Path/Symbol:** `lib/linter/code-path-analysis/code-path-segment.js:CodePathSegment` (:45–260).
**Signature:** `constructor(id, allPrevSegments, reachable)`; factories `newRoot(id)`, `newNext(id, allPrevSegments)`, `newUnreachable(id, allPrevSegments)`, `newDisconnected(id, allPrevSegments)`; statics `markUsed(segment)`, `markPrevSegmentAsLooped(segment, prevSegment)`, `flattenUnusedSegments(segments)`.
**Data Shape:** four edge arrays — `prevSegments`/`nextSegments` (reachable-only view) and `allPrevSegments`/`allNextSegments` (full view); frozen `internal.used` flag + `internal.loopedPrevSegments`. A fresh segment is *detached*: it knows its predecessors but they don't know it.

### Decisive source
```js
static markUsed(segment) {
  if (segment.internal.used) return;
  segment.internal.used = true;
  if (segment.reachable) {
    for (const prevSegment of segment.allPrevSegments) {
      prevSegment.allNextSegments.push(segment);
      prevSegment.nextSegments.push(segment);      // reachable: both views
    }
  } else {
    for (const prevSegment of segment.allPrevSegments) {
      prevSegment.allNextSegments.push(segment);   // unreachable: full view only
    }
  }
}
// newNext flattens unused (speculative) predecessors into THEIR predecessors,
// so a never-entered branch leaves no phantom node in the chain:
static newNext(id, allPrevSegments) {
  return new CodePathSegment(id, CodePathSegment.flattenUnusedSegments(allPrevSegments),
    allPrevSegments.some(isReachable));
}
```

**Flow:** `makeNext/makeUnreachable` create detached segments; walking onto one (`forwardCurrentToHead`) calls `markUsed`, which back-writes the forward edges. `flattenUnusedSegments` substitutes an unused segment by its own `allPrevSegments` (Set-deduped), recursively erasing unwalked chains from lineage.
**Invariant:** `newUnreachable` marks its product used immediately — the comment is explicit: in `if (a) return a; foo();` the unreachable segment after the return "is not used but must not be removed", or `no-unreachable`-style rules lose their anchor; reachable/unreachable dual views are kept on ONE object so rules can ask either question without re-traversal; loop edges are tagged via `loopedPrevSegments`, not regular prev/next pushes.
**Probe:** `tests/lib/linter/code-path-analysis/code-path-analyzer.js` (:158–254 public-segment-interface assertions over id/next/allNext/prev/allPrev/reachable).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "CodePathSegment markUsed flattenUnusedSegments newUnreachable", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.code-path-analysis.code-path-segment.CodePathSegment.markUsed" });
```

## Verdict
Adopt the two-view edge arrays + used-flag lazy attachment + unreachable-tail retention; adapt reachability to your IR's notion of executability; omit debug `internal.nodes` collection unless you need per-segment AST traces.
