<!-- capsule-v2 -->
# Append cache with trailing-byte carry — how does a read cache stay correct when a writer appends mid-line between reads?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** a porter must decide how to avoid re-reading a growing JSONL file on every poll without ever emitting an event whose bytes were only partially flushed.

## Size+mtime+flag-keyed per-file cache; range read of appended bytes; last-newline split with unterminated-tail carry
**Path/Symbol:** `src/main/activity-event-file.ts:parsedFileEvents` (209-251), `:readFileRange` (253-267), `:parseEventChunk` (269-286); cache decl at 86-94 (`EVENT_FILE_CACHE_LIMIT = 128`).
**Signature:** `parsedFileEvents(dataDirectory, file, options): ActivityEvent[]`; `parseEventChunk(bytes: Buffer): { events: ActivityEvent[]; trailingBytes: Buffer }`.
**Data Shape:** cache entry `{size, modifiedMs, captureEmailActivity, captureMessagingActivity, events, trailingBytes}` in an insertion-ordered Map keyed by resolved path.

### Decisive source
```ts
if (cached && cached.captureEmailActivity === captureEmailActivity &&
    cached.captureMessagingActivity === captureMessagingActivity && stats.size > cached.size) {
  const appended = readFileRange(path, cached.size, stats.size - cached.size);
  const parsed = parseEventChunk(Buffer.concat([cached.trailingBytes, appended]));
  events = [...cached.events, ...parsed.events];
  trailingBytes = parsed.trailingBytes;
}
```
and the split:
```ts
const finalNewline = bytes.lastIndexOf(0x0a);
...
const finalEvent = parseRawActivityEvent(unterminated.toString("utf8"));
return finalEvent
  ? { events: [...events, finalEvent], trailingBytes: Buffer.alloc(0) }
  : { events, trailingBytes: Buffer.from(unterminated) };
```

**Flow:** stat file → full-entry hit if size+mtime+both capture flags match → append-only fast path if flags unchanged and size grew (read ONLY `[cached.size, stats.size)` via a short-read-safe `readSync` loop with fd closed in `finally`) → prepend the previous unterminated tail → split at last `\n`. A trailing fragment is promoted to a real event if it fully parses as-is, otherwise it stays `trailingBytes` until its newline arrives. Any flag change or size shrink falls back to a full re-read. Insertions delete-then-set so re-reads move to MRU; eviction drops the oldest key past 128 entries.
**Invariant:** no partial line is ever emitted as an event, and each completed line is emitted exactly once across successive polls — including an event written by two separate `write()` calls (the test splits one mid-UTF-8-multibyte).
**Probe:** `src/main/activity-event-file.test.ts:156-173` ("recovers an event appended across two partial writes": first load → `[]`, after the rest + newline arrives → exactly `["partial"]`); `107-128` ("invalidates the event cache when messaging capture changes": same file toggles between `[]` and `["messages"]` purely on flags). Runner note: suite blocked by missing `node_modules`; verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "event file cache trailing bytes appended range", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt trailing-byte carry and flag-sensitive invalidation for any tail-following reader over append-only logs; adapt the capture-flag pair to whatever filter options change your parse output; omit Node sync-fs specifics if porting to async hosts (but keep the short-read loop semantics). Coverage checked: `no_recorded_issue`.
