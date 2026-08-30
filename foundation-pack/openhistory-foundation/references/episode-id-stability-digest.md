<!-- capsule-v2 -->
# Episode id stability — how can a derived record keep pointing at the same episode while that episode is still growing?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** What must an episode identifier be derived from so re-segmenting a growing event log never orphans already-persisted derived items?

## makeEpisode identity digest
**Path/Symbol:** `src/main/episode-segmenter.ts:makeEpisode` (lines 104-119).
**Signature:** `makeEpisode(events: ActivityEvent[]): ActivityEpisode` (internal; identity = first work-evidence event).
**Data Shape:** events → `{ id: "<timestamp-slug>-<12-hex>", startTime, endTime, events, applications }`; slug is the identity event's ISO timestamp with `:`→`-` and `.mmmZ`→`Z`.

### Decisive source
```ts
const identityEvent = events.find(isWorkEvent) ?? first;
const identity = identityEvent.id;
const digest = createHash("sha256").update(identity).digest("hex").slice(0, 12);
const startSlug = identityEvent.timestamp.replaceAll(":", "-").replace(/\.\d{3}Z$/, "Z");
return { id: `${startSlug}-${digest}`, ... };
```

**Flow:** flush() calls prepareEpisodeEvents first (trim/coalesce), so makeEpisode sees the prepared window → identity anchor is the FIRST WORK EVENT, not the first event — leading context (≤30 s lead) cannot shift the id → same input ⇒ same id, and appending later events to the same open episode leaves the id untouched.
**Invariant:** the id depends only on the identity event's `id` + `timestamp`; it must not depend on episode length, end time, or any later event. This is what lets `TimelineCoordinator` and `reconcileProtectedHistory` treat episode ids as stable foreign keys across re-segmentation.
**Probe:** `src/main/episode-segmenter.test.ts:61-74` — executed GREEN at pin: "episode identifiers are stable for the same source events" and "stay stable while the active episode grows"; also :154-162 pins that trimming stale leading context yields the SAME id as segmenting the lone work event.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "makeEpisode sha256 identity digest stable", limit: 10 });
```
Executed live byte-for-byte: top rows are the `episode-segmenter` group (`makeEpisode`, `segmentActivityEvents`, `prepareEpisodeEvents`); no unrelated subsystem ranks above it.

## Verdict
Adopt content-anchored deterministic ids for streaming-derived records (anchor on the earliest *meaningful* item, hash its key); adapt the slug format and digest width to your storage naming rules; omit the specific work-kind list. Coverage: `no_recorded_issue` on `src/main/episode-segmenter.ts`; probe suite executed green at pin.
