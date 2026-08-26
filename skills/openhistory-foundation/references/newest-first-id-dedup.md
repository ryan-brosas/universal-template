<!-- capsule-v2 -->
# Newest-first id dedup — how do you stop reading once you hold the newest N unique events across many files?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** a porter must decide dedup direction (first-wins from which end?) and how to bound I/O when only the newest slice is needed.

## Reversed walk, first-wins Map, labeled outer break
**Path/Symbol:** `src/main/activity-event-file.ts:loadNewestEvents` (190-207).
**Signature:** `loadNewestEvents(dataDirectory: string, files: string[], limit: number, options: ActivityPrivacyOptions): Map<string, ActivityEvent>`.
**Data Shape:** pre-sorted file list (oldest→newest) + non-negative limit in; insertion-ordered `Map<event.id, ActivityEvent>` out; empty Map when limit is 0.

### Decisive source
```ts
const events = new Map<string, ActivityEvent>();
if (limit === 0) return events;

newestFiles: for (const file of [...files].reverse()) {
  for (const event of [...parsedFileEvents(dataDirectory, file, options)].reverse()) {
    if (events.has(event.id)) continue;
    events.set(event.id, event);
    if (events.size >= limit) break newestFiles;
  }
}
return events;
```

**Flow:** files reversed (newest shard first) → each shard's parsed events reversed (newest line first) → first sighting of an id wins → labeled `newestFiles:` break exits BOTH loops the moment the map reaches `limit`. Because shards are date-named and lines are roughly append-ordered, the walk reads as few files as possible.
**Invariant:** newest occurrence of an id always wins; at most `limit` distinct ids are ever parsed-and-held even though a shard may contain thousands of lines; duplicates never consume budget (`continue`, not `set` overwrite).
**Probe:** `src/main/activity-event-file.test.ts:130-154` — duplicate id `"new"` appears twice in one file; `loadActivityEvents(directory, 2)` still returns exactly `["middle", "new"]` after timestamp sort. Runner note: suite blocked by missing `node_modules`; verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "loadNewestEvents dedup limit reverse files", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt first-wins-from-newest-end dedup with the labeled double-loop break; adapt the per-file parser to your format; omit the privacy-filter coupling if your stream has no protected records. Coverage checked: `no_recorded_issue`.
