<!-- capsule-v2 -->
# Adaptive table column budget — how do N secondary metrics + description share one terminal line?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** Which columns get full width, which get dropped, and when does the "..." ellipsis column appear?

## renderDashboardLines smart sizing — essentials full, secondaries fit-scan, desc floor 25%
**Path/Symbol:** `extensions/pi-autoresearch/src/dashboard/table.ts:198–296` (sizing), :324–332 (earlier-runs note), :361–366 (commit dash for non-keep).
**Signature:** `renderDashboardLines(st, width, th, maxRows=6, worktreePath=null): string[]`; `maxRows=0` ⇒ fullscreen mode (unlimited rows + scatter chart).
**Data Shape:** columns idx | commit | ★primary | [secondaries…] | [...?] | status | description; `minGap=2`.

### Decisive source
```ts
const minDescWidth = Math.max(25, Math.floor(width * 0.25));
for (let i = 0; i < finalSecWidths.length; i++) {
  const secW = finalSecWidths[i].width;
  const wouldHaveHidden = finalSecWidths.length > i + 1;
  const neededWidth = fixedColsW + accumulatedSecW + secW + (wouldHaveHidden ? 5 : 0) + minDescWidth;
  if (neededWidth < width) { visibleSecCount++; accumulatedSecW += secW; }
  else break;                                    // first non-fitting secondary stops the scan (no reorder)
}
```

**Flow:** visible rows = last maxRows (with `… N earlier runs` header when truncated) → per-column content widths measured over VISIBLE rows only → essential four always render at content+gap → secondary metrics admitted left-to-right while the running total leaves room for: remaining hidden-secondaries ellipsis (5 chars) + description floor (max(25, 25% width)) → leftover becomes desc width. Non-keep rows show `—` in commit column (a discarded run has no commit by the revert contract). Row coloring: primary success/error vs BASELINE (not vs best), secondary success iff `val <= baselineSecondary[name]` (direction-blind — a known quirk to preserve or fix knowingly).
**Invariant:** the fit-scan is order-preserving and prefix-only: a wide early metric blocks later narrow ones rather than reordering (column stability beats density). The +5 reservation guarantees the ellipsis column never appears without room. Description always keeps ≥25% so the human-readable what/why survives any metric count.
**Probe:** anchors: `grep -n 'reservedForRecent' extensions/pi-autoresearch/src/dashboard/scatter-plot.ts | wc -l` → 2 (chart sibling); table anchors `grep -n 'minDescWidth' extensions/pi-autoresearch/src/dashboard/table.ts | wc -l` → 2 (:254 def, :262 use); `grep -n "commitDisplay = '—'" extensions/pi-autoresearch/src/dashboard/table.ts` → :363.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "renderDashboardLines visibleSecCount minDescWidth ellipsis", limit: 10 });
```

## Verdict
Adopt the prefix-fit budget with reserved ellipsis and description floor verbatim; adapt column set/ordering to your schema; note-and-choose on the direction-blind secondary coloring quirk. Coverage caveat: renderer untested directly (fullscreen-width.test covers overlay fitting only) — source-pinned.
