<!-- capsule-v2 -->
# Derived-store privacy reconciliation — after purging protected raw records, how do you find and delete every derived summary that depended on them?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** How does a scrub of the raw event store cascade into tiered derived stores without re-summarizing or losing safe items?

## reconcileProtectedHistory
**Path/Symbol:** `src/main/privacy-reconciler.ts:reconcileProtectedHistory` (lines 16-63) with `TimelineStore.replaceAll` (`src/main/timeline-store.ts:53-63`) and `writePrivateFile` (`src/main/private-storage.ts:8-13`).
**Signature:** `reconcileProtectedHistory(dataDirectory, timelineStore, hourStore, dailyRollupStore, options?): PrivacyReconciliationResult`.
**Data Shape:** returns per-tier removed counts `{rawEventsRemoved, timelineItemsRemoved, hourItemsRemoved, dailyRollupsRemoved}`; provenance keys: timeline item → `sourceEventIds`; hour item → `sourceTimelineIds` + `sourceTimelineRevisions`; rollup → `sourceTimelineRevisions`.

### Decisive source
```ts
const rawEventsRemoved = scrubProtectedActivityEvents(dataDirectory, options);
const episodes = new Map(segmentActivityEvents(
  loadActivityEvents(dataDirectory, undefined, options), options
).map((episode) => [episode.id, episode.events.map((event) => event.id)]));
const timeline = allTimeline.filter((item) => {
  const sourceEventIds = episodes.get(item.id);
  return Boolean(sourceEventIds && sameValues(item.sourceEventIds ?? [], sourceEventIds));
});
...
const hours = allHours.filter((item) => {
  const sourceItems = item.sourceTimelineIds.flatMap((id) => timelineById.get(id) ?? []);
  if (sourceItems.length !== item.sourceTimelineIds.length) return false;
  const revisions = sourceItems.flatMap((s) => timelineRevision(s) ?? []).sort();
  return sameValues(item.sourceTimelineRevisions, revisions);
});
```

**Flow:** physically scrub raw shards → reload + RE-SEGMENT once → rebuild Map(episode.id → ordered event ids) → tier 1: keep timeline items whose id regenerates AND whose `sourceEventIds` match order-exactly → tier 2: keep hour items only if every referenced timeline id resolves AND their recomputed sorted revision list equals the stored one (`timelineRevision(item) = ${id}:${sha256(sourceEventIds.join("\n")).slice(0,16)}`) → tier 3: keep rollups only if every stored revision still exists in the surviving timeline set → each tier calls `replaceAll` ONLY when something was dropped; return removed counts.
**Invariant:** deletion is conservative in the right direction — any provenance that fails to REPRODUCE exactly is dropped, and a surviving item's markdown file is guaranteed present because `replaceAll` unlinks `.md` files for every id no longer retained and rewrites `index.json` via pid-tagged 0600 temp+rename (`writePrivateFile`). No derived content is regenerated during reconciliation.
**Probe:** `src/main/privacy-reconciler.test.ts:15-113` — read directly at pin (suite load BLOCKED by standing no-node_modules `zod`, recorded honestly): private browsing interval is purged from raw JSONL AND all three derived stores incl. on-disk `private-episode.md`; the preserved-burst test asserts an exact all-zero result object and full survival.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "reconcileProtectedHistory replaceAll timelineRevision", limit: 10 });
```
Executed live byte-for-byte: top rows are `privacy-reconciler.reconcileProtectedHistory`, `timelineRevision` (`provenance.ts`), and the store group; trace confirms sole caller is `initialize`.

## Verdict
Adopt reproduce-then-compare reconciliation (regenerate provenance from source of truth; drop what doesn't match exactly; write only when changed); adapt tier definitions to your projection DAG; omit the specific three-tier layout. Coverage: `no_recorded_issue` on privacy-reconciler/timeline-store/provenance/hour-store/daily-rollup-store paths; reconciler probe is a direct-test READ with runner block recorded — not a green run.
