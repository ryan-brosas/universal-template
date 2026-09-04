<!-- capsule-v2 -->
# Reachability predicate for segment sets — the one-line helper code-path rules share

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** When a rule asks "can execution still reach here?" across a set of CPA segments, what is the exact shared contract?

## isAnySegmentReachable
**Path/Symbol:** `lib/rules/utils/code-path-utils.js:isAnySegmentReachable(segments)` (:10–20).
**Signature:** `isAnySegmentReachable(segments: Set<CodePathSegment>): boolean`.
**Data Shape:** iterates the Set directly; true iff ≥1 member has `reachable === true`; EMPTY set ⇒ false.

### Decisive source
```js
function isAnySegmentReachable(segments) {
  for (const segment of segments) { if (segment.reachable) return true; }
  return false;
}
```

**Flow:** early-return scan.
**Invariant:** empty-set ⇒ false is the semantic choice that matters: "no path reaches this" rather than vacuous truth — callers in no-unreachable/no-fallthrough-style rules rely on it to flag dead code whose segment sets have been fully flattened away (see cpa-segment-lazy-attachment: flattenUnusedSegments erases unwalked chains). The helper exists because several rules independently reimplemented this loop with subtle bugs (some treating empty as reachable). It reads `segment.reachable` — the CPA's per-segment liveness flag maintained by fork/merge algebra — NOT `segment.isReached`-style internal bookkeeping.
**Probe:** `tests/lib/rules/utils/code-path-utils.js` (:21–56 six-case truth table: empty⇒false, single reachable/unreachable, all-unreachable⇒false, any-reachable⇒true).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "isAnySegmentReachable code-path-utils", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.code_path_utils.isAnySegmentReachable" });
```

## Verdict
Adopt as the single reachability oracle over segment/lane collections; the whole capsule is the empty-set ruling plus which flag to read.
