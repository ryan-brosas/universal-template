<!-- capsule-v2 -->
# RouteConflictDetector — when do two declared routes collide, and which conflicts does specificity sorting legitimately erase?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How do you decide two route patterns can match the same request — and how do you avoid erroring on shadows that sorting already fixed?

## tokenizePath / pathsCanOverlap / detect / handle / filterSortResolvedShadows
**Path/Symbol:** `packages/core/router/route-conflict-detector.ts:tokenizePath` (:36-62), `pathsCanOverlap` (:68-107), `detect` (:114-171), `handle` (:178-203), `filterSortResolvedShadows` (:224-241), host RegExp guard (:310-330).
**Signature:** `static tokenizePath(rawPath): {kind:'literal'|'param'|'wildcard', value}[]`; `static detect(routes, versioningOptions): RouteConflict[]`; `static handle(conflicts, policy, logger): void`.
**Data Shape:** Conflict = `{winner (earlier), shadowed (later), kind: 'duplicate'|'shadow'}`; policy per-kind `'off'|'warn'|'error'`; supports bare wildcards (`*path`) AND adapter-normalized groups (`{*path}`).

### Decisive source
```ts
// length mismatch: only the SHORTER side's trailing wildcard can absorb
if (leftSegments.length !== rightSegments.length) {
  const shorterEndsInWildcard = left.length < right.length ? leftEnds : rightEnds;
  if (!shorterEndsInWildcard) return false;
}
// segment compare — wildcard or param overlaps anything; literals must match:
if (l.kind === 'wildcard' || r.kind === 'wildcard') return true;
if (l.kind === 'param' || r.kind === 'param') return true;
return l.value === r.value;

// stateful-flag guard for host RegExps reused across many pair comparisons:
leftValue.lastIndex = 0;
return leftValue.test(rightValue as string);
```

**Flow:** unique-pair walk → method gate (`ALL` matches all) → version gate (no config or URI ⇒ always overlap; else neutral/undefined matches any, arrays intersect) → host gate (undefined = wildcard; regexp-vs-string via anchored test with lastIndex reset; regexp-vs-regexp assumed overlapping) → path gate → classify identical (method+path+host-set-equal+version-set-equal, order-INsensitive arrays) vs shadow → policy application aggregates ALL error-level messages into ONE RouteConflictException.
**Invariant:** `filterSortResolvedShadows` runs AFTER specificity sorting and drops every shadow whose winner was declared LATER but sorted FIRST — the sort promoted it, so runtime behavior is correct and `shadow:'error'` must not abort. Shadows where the winner was already first in declaration order are genuine and kept; duplicates are ALWAYS kept. Forgetting this filter makes the error policy unusable alongside the sorter.
**Probe:** `packages/core/test/router/route-conflict-detector.spec.ts` — shorter-side-wildcard asymmetry :101/:119, g-flag lastIndex consistency :335, order-insensitive host duplicate :362, handle policy matrix :397-557, filterSortResolvedShadows :558.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouteConflictDetector pathsCanOverlap filterSortResolvedShadows shadow duplicate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-gate pair classifier + sort-aware shadow filtering as a compile-time router lint; adapt the tokenizer grammar to your pattern syntax (keep `{*x}` normalization awareness); omit version/host gates for method-only routers. Porting wrong: treating longer-side trailing wildcards as absorbing (they require ≥1 matched segment), or running detect() before sorting without the shadow filter.
