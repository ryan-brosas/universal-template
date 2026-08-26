<!-- capsule-v2 -->
# Fail-soft shard loader — how does a caller load the newest N events across daily shards without any error path escaping?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** a porter must decide whether missing/corrupt storage crashes, returns partial data, or returns empty — and where the `limit` is applied when filtering can shrink the result.

## Sorted-shard read with filter-then-trim limit and catch-to-empty contract
**Path/Symbol:** `src/main/activity-event-file.ts:loadActivityEvents` (115-136).
**Signature:** `loadActivityEvents(dataDirectory: string, limit?: number, options?: ActivityPrivacyOptions): ActivityEvent[]`.
**Data Shape:** directory path + optional limit in; timestamp-ascending filtered events out; never throws (readdir/read failures → `[]`).

### Decisive source
```ts
const files = readdirSync(dataDirectory)
  .filter((name) => name.startsWith("events-") && name.endsWith(".jsonl"))
  .sort();
const events = limit === undefined
  ? loadAllEvents(dataDirectory, files, options)
  : loadNewestEvents(dataDirectory, files, Math.max(0, limit), options);

const sorted = [...events.values()].sort(
  (left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp)
);
const protectedFiltered = filterProtectedActivityEvents(sorted, options);
return limit === undefined ? protectedFiltered : protectedFiltered.slice(-limit);
} catch {
  return [];
}
```

**Flow:** shard selection by prefix/suffix (lexicographic sort = chronological because names embed dates) → bounded or full parse → global timestamp sort → stateful privacy filter → final trim. The limit is applied twice on purpose: first as a read bound (`Math.max(0, limit)`, 0 short-circuits to empty), then again after filtering because boundary sentinels and drops change the set size.
**Invariant:** the whole body sits in one try whose catch returns `[]` — an unreadable store is indistinguishable from an empty one at the type level; callers like `TimelineCoordinator.getState` and seven CLI scripts rely on this.
**Probe:** `src/main/activity-event-file.test.ts:130-154` ("bounded loading returns the newest valid unique events across daily files": limit 2 → exactly `["middle","new"]` from two shards with junk line and duplicate ids present; limit 0 → `[]`; after append, limit 1 → only the new event). Runner note: suite blocked here by missing `node_modules`; assertions verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "load activity events shard limit", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt fail-soft empty-array error shape and filter-aware double trim; adapt shard naming/globbing to your storage layout; omit the Electron-specific capture-flag plumbing. Coverage checked: `no_recorded_issue`, generation matches pin.
