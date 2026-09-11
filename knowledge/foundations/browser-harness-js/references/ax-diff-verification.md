<!-- capsule-v2 -->
# axDiff — how do you verify an action landed without re-feeding the whole next tree into context?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What normalization makes two snapshots of a mutating page comparable?

## Ref-stripped keys, LCS line diff, unchanged lines omitted
**Path/Symbol:** `skills/cdp/sdk/axview.ts:normalizeLine` (:372-375) + `axDiff` (:387-439).
**Signature:** `axDiff(prev: string, next: string): string` → `- old line` / `+ new line`, or `(no changes)`.
**Data Shape:** input = two axView strings; ref-map lines (`# refs …`) and pure payload lines (`^(\[\d+\]=\d+\s*)+$`) are filtered before compare.

### Decisive source
```ts
const normalizeLine = (line: string): string => line.replace(/\[\d+\]\s+/g, '');  // refs renumber every snapshot
...
dp[i]![j] = a[i]!.key === b[j]!.key
  ? dp[i + 1]![j + 1]! + 1
  : Math.max(dp[i + 1]![j]!, dp[i]![j + 1]!);
```

**Flow:** split both views into lines → drop blank, refs-header, and ref-map payload lines → key each line by its ref-stripped form (raw line kept for display) → LCS over keys → walk the matrix emitting `-`/`+` for non-matching stretches in order.
**Invariant:** compare on NORMALIZED keys but print RAW lines (trimmed-left), so the model sees real `[n]` labels while renumbering never produces phantom diffs. Identical trees return the literal `(no changes)` sentinel.
**Probe:** behavior is pinned by the round-trip tests of axView plus source pins: `grep -n "lastIndexOf\|no changes" skills/cdp/sdk/axview.ts`. No dedicated axDiff unit test — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "axDiff", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ref-stripped-LCS as the standard verify step in any snapshot-act-resnapshot loop; adapt to whatever your view format numbers; omit at your peril — feeding full next-trees per step is the token cost this capsule exists to delete.
