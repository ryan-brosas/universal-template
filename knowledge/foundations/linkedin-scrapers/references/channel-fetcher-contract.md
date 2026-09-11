<!-- capsule-v2 -->
# Channel-fetcher registry contract — how do I add a new incremental event type (e.g. "invitation accepted") without touching the pagination/scheduling engine?

**Source:** lh-basis NO-LICENSE extract `core/local-source/dist/Analytics/*` (learn-only — patterns, never code); Codebase Memory `lh-basis` umbrella project — same outside-roots caveat as `durable-named-cursor-continuation.md`. **Question:** what interface must one class implement so a generic batch provider can discover, fetch, and cursor-track it?

## Fetcher/codec registration pair
**Path/Symbol:** `Analytics/DataFetchers/{InviteAcceptedDataFetcher.js, MessageReplyRecievedDataFetcher.js}` + `Analytics/Providers/EventsBatchProvider.js:EventsBatchProvider` constructor loop over `registerFetchers`.
**Signature:** the de-facto interface (from both twins): `getChannelName() -> CHANNEL_NAMES.*`; `getInitialCursorValue() -> {date: Date, id: number}`; `extractNextCursorData(lastItem?) -> {date, id} | null`; `mapToEvents(rows) -> [{type, id, date, liAccountId, personId, …}]`; `async fetchBatch(source, {date,id}, limit) -> rows[]`. Registration: `new EventsBatchProvider(source, registerFetchers=[{fetcher, codec}], batchSize=1000)`; consumer side: `fetchData(channelNames?, size) -> Map<channelName, {events, nextCursorData}>`, then per channel `commitCursor(name, nextCursorData)`.
**Data Shape:** every event row carries `type` discriminator + `liAccountId` + `personId` + source ids (`messageId` or `resultId`) + `date`; fetchers return RAW result rows; `mapToEvents` projects them into typed events.

### Decisive source
```js
// EventsBatchProvider constructor — discovery IS data:
for (const {fetcher, codec} of this.registerFetchers) {
    const name = fetcher.getChannelName();
    this.channelNames.add(name);
    this.fetcherByChannelNameMap.set(name, fetcher);
    this.cursorCodecByChannelNameMap.set(name, codec);
}
// unknown names fail LOUDLY, never silently no-op:
getExistingFetcher(n){ const f = this.fetcherByChannelNameMap.get(n);
  if (!f) throw new Error(`Fetcher for channel ${n} is not found`); return f }

// twin A — InviteAccepted: semantic pre-filter INDEPENDENT of resume position
profileFilter:{ resultStatuses:{in:[ActionResultStatus.Successful]},
  actionTypes:{in:["InvitePerson","InvitePersonByEmail"]},
  collectingItemsProps:{people:{connectedAt:{gte: epoch}}},   // epoch from getInitialCursorValue()
  …resultCreatedAt:{gte: cursorDate}, resultId:{gt: cursorId}, sort:"+result_created_at"}

// twin B — MessageReplyReceived: ONE result fans out to MANY message events,
// each carrying its parent's cursor fields so continuity survives the fan-out:
.filter(({messagesInfo}) => Boolean(messagesInfo))
.flatMap(e => e.messagesInfo.map(m => ({resultId: e.id, messageId: m.message.id,
  messageSentAt: m.sendAt, resultCreatedAt: e.resultInfo.createdAt, …})))
```

**Flow:** author a new fetcher class → implement the five methods → hand `[ {fetcher, codec} ]` to the provider → provider indexes by `getChannelName()` → `fetchData()` loops channels (all when called with no filter) → per channel: cursor resolve → `fetchBatch` → `extractNextCursorData(last)` → `mapToEvents` projection.
**Invariant:** (1) **Open/closed extension**: adding an event type = adding ONE class + one registry entry; the provider, codec, storage schema, and scheduler never change — that is the whole point of routing everything through `getChannelName()`. (2) **Loud unknown-channel errors** (`Fetcher for channel X is not found`) instead of silent empty results. (3) Fan-out rows MUST carry parent cursor fields (`resultCreatedAt`/`resultId`) on EVERY emitted event or the composite cursor loses meaning after a crash mid-batch. (4) The semantic pre-filter (invite status/action-type) is independent of the resume window — never merge domain filtering INTO cursor math.
**Probe:** deterministic twin-contrast probes (no upstream tests in dist extract — coverage caveat recorded; anchored at `lh-basis/core/local-source/dist/Analytics/DataFetchers`): `grep -c "flatMap\|filter" MessageReplyRecievedDataFetcher.js` ≥ 1 vs plain `.map` in InviteAccepted; both files define identical `getInitialCursorValue` epochs `2024-01-01T00:00:00.000Z` but DIFFERENT `type` strings (`"message_reply_received"` vs `"invitation_accepted"`); provider throws on unregistered names (two distinct error strings for fetcher-vs-codec lookup).

## Get live surrounding code
**Retrieve:**
```ts
// Outside indexed graph roots — recorded coverage caveat; read sources directly:
// <root>/Analytics/Providers/EventsBatchProvider.js (constructor + fetchData/commitCursor)
// <root>/Analytics/DataFetchers/{InviteAcceptedDataFetcher.js,MessageReplyRecievedDataFetcher.js}
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "analytics_cursor", limit: 5 }); // returns 0 — expected
```

## Verdict
Adopt: channel-name-keyed registries with loud miss errors, `{fetcher, codec}` registration pairs, epoch defaults owned by the fetcher, raw-row→typed-event projection at the boundary, and fan-out rows carrying parent cursor fields. Adapt event vocabularies and storage to host. Omit vendored code (no-license, patterns only). Runner-up pattern in-suite: linvo-scraper's flat service registry (`linvo-service-taxonomy.md`) achieves the same open/closed goal at the ACTION level — use lh-basis's shape for EVENT streams, linvo's for page-driven actions.
