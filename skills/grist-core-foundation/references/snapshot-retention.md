<!-- capsule-v2 -->
# Snapshot retention policy — which versions of a document does time travel keep?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Given a version list newest-first, what pure function decides keep/prune so retention survives timezone, labels, and payment windows?

## Time-bucketed keep ladder over newest-first snapshots
**Path/Symbol:** `app/server/lib/DocSnapshots.ts:shouldKeepSnapshots` (whole function ~322–395 + `updateAndCheckRange` tail), consumed by `DocSnapshotPruner.classify/prune` (52–76).
**Signature:** `function shouldKeepSnapshots(snapshots: ObjSnapshotWithMetadata[], snapshotWindow?: SnapshotWindow): boolean[]`.
**Data Shape:** input ordered MOST-RECENT-FIRST; each snapshot carries `lastModified` ISO ts and optional `metadata.tz`, `metadata.label`; bucket caps from env JSON `GRIST_SNAPSHOT_TIME_CAP` (default `{"hour":25,"day":32,"isoWeek":12,"month":96,"year":1000}`); recents via `GRIST_SNAPSHOT_KEEP` (default 5).

### Decisive source
```ts
// Keep: 5 most recent; most recent per hour (25), per day (32), per isoWeek (12),
// per month (96), per year (1000); labelled versions for 32 days. UTC/ISO weeks.
return snapshots.map((snapshot, index) => {
  if (index === 0) { return true; }                    // never delete the current version
  const date = moment.tz(snapshot.lastModified, tz);
  if (snapshotWindow && start.diff(date, snapshotWindow.unit, true) > snapshotWindow.count) {
    return false;                                      // paid window overrides everything
  }
  let keep = index < integerParam(process.env.GRIST_SNAPSHOT_KEEP || 5, "GRIST_SNAPSHOT_KEEP");
  for (const bucket of buckets) {
    if (updateAndCheckRange(date, bucket)) { keep = true; }   // first-seen-in-bucket wins
  }
  if (snapshot.metadata?.label && start.diff(date, "days") < 32) { keep = true; }
  return keep;
});
function updateAndCheckRange(t: moment.Moment, bucket: TimeBucket) {
  if (bucket.usage < bucket.cap && !t.isSame(bucket.prev, bucket.range)) {
    bucket.prev = t; bucket.usage++;
    return true;
  }
  return false;
}
```

**Flow:** walk newest→oldest; index 0 always kept → outside paid window ⇒ prune immediately → keep if among N most recent OR it is the FIRST version seen in a new hour/day/ISO-week/month/year bucket whose quota isn't exhausted (each kept version can consume quota in several buckets at once — deliberate, because alternatives feel counter-intuitive per the docstring) OR it's labelled and ≤32 days old. All comparisons use the document's own timezone (`metadata.tz`, defaulting UTC), Gregorian calendar, Monday-start ISO weeks.
**Invariant:** the current version is undeletable regardless of inputs; the function is PURE (bucket state local to the call) so classification is reproducible and testable against human-readable timelines; a version that misses every bucket AND the recent window is pruned even if adjacent kept versions are seconds away; env-overridable caps make the whole policy tunable without code changes.
**Probe:** `test/server/lib/DocSnapshots.ts::"selects reasonable versions to prune in a 10 day history"` (:85), `::"...100 day history"` (:109), `::"selects versions that allow gaps"` (:133), `::"respects document timezone"` (:253), `::"favors labelled versions"` (:282), `::"eventually discards labelled versions"` (:299), `::"enforces the snapshot window"` (:312) — tests encode expected keep/prune strings for full timelines.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "shouldKeepSnapshots DocSnapshotPruner", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure keep-ladder (recents ∩ first-per-bucket-with-caps ∩ recent-labels, window override, current-version guard) for ANY versioned store — S3 object versions, file backups, DB snapshots; the ladder needs only timestamps in, booleans out. Adapt bucket ranges/caps, calendar semantics, and label TTL to product needs. Omit moment-tz if your timestamps are already normalized, but preserve "decide from metadata alone, no I/O inside the predicate."
