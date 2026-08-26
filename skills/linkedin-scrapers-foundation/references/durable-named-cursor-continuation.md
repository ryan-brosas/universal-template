<!-- capsule-v2 -->
# Durable named-cursor continuation — how do I resume an incremental event scan per account per channel across restarts without skipping or duplicating rows?

**Source:** lh-basis NO-LICENSE extract `core/local-source/dist/Analytics/*` (learn-only — record the pattern, never copy code); Codebase Memory `lh-basis` (umbrella) — **coverage caveat:** the Analytics plane sits OUTSIDE both indexed roots (`lh-basis` excludes `core/local-source/dist`; `lh-basis-source` roots at `dist/Source`), so graph retrieval returns zero here — direct source paths below are the probe surface. **Question:** what cursor shape survives same-timestamp ties, persists durably, and separates "fetched" from "safely consumed"?

## Codec + repo + batch-provider triad
**Path/Symbol:** `Analytics/Cursors/Codecs/TimestampBigIntCodec.js:TimestampBigIntCodec` (encode/decode, DELIMITER `"|"`, ID_PAD_LENGTH `20`); `Analytics/Cursors/Codecs/CursorCodec.js:CursorCodec` (empty base class = codec interface); `Analytics/AnalyticsCursorRepo.js:analyticsCursorRepo` (`DBModelsRepo("analytics_cursor", …)`); `Analytics/Providers/EventsBatchProvider.js:EventsBatchProvider` (`fetchDataForChannel`/`fetchData`/`commitCursor`/`getCurrentCursor`).
**Signature:** `encode(cursor {date: Date, id: number}) -> "${date.getTime()}|${id.toString().padStart(20,'0')}"`; `decode(position: string) -> {date, id}` throwing `` `Invalid cursor format: ${cursor}` `` unless both parts pass `isNonNegativeInteger`; `async fetchDataForChannel(channelName, batchSize=1000) -> {events, nextCursorData}`; `async commitCursor(channelName, cursorData)`; `getInitialCursorValue() -> {date: new Date("2024-01-01T00:00:00.000Z"), id: 0}`.
**Data Shape:** storage row `{id PK, li_account_id INTEGER UNIQUE, name TEXT UNIQUE, position TEXT}` — ONE opaque string per (account, channel-name); UNIQUE constraints make the cursor key implicit in the schema. In-memory: `registerFetchers` receives `[{fetcher, codec}]`; provider builds `channelNames: Set`, `fetcherByChannelNameMap`, `cursorCodecByChannelNameMap`.

### Decisive source
```js
// TimestampBigIntCodec — composite (time, id) cursor, zero-padded so the
// numeric tail never changes width mid-stream:
encode(e){ const t = e.id.toString().padStart(this.ID_PAD_LENGTH, "0");
           return `${new Date(e.date).getTime()}${this.DELIMITER}${t}` }
decode(e){ const [t, r] = e.split(this.DELIMITER);
           if (!isNonNegativeInteger(Number(t)) || !isNonNegativeInteger(Number(r)))
               throw new Error(`Invalid cursor format: ${e}`);
           return { date: new Date(parseInt(t,10)), id: parseInt(r,10) } }

// EventsBatchProvider.fetchDataForChannel — fetch returns the NEXT cursor,
// persistence is a SEPARATE commit call:
const cursor   = await this.getCurrentCursor(channel, fetcher, codec); // stored ?? initial
const batch    = await fetcher.fetchBatch(this.source, cursor, size);
const nextData = fetcher.extractNextCursorData(batch[batch.length-1]); // null when batch empty
return { events: fetcher.mapToEvents(batch), nextCursorData };
// getCurrentCursor: repo.findOne({filters:{liAccountId: In([id]), name: In([ch])}})
//                   ? codec.decode(row.position) : fetcher.getInitialCursorValue()
```

**Flow:** startup → per channel `getCurrentCursor` (decode stored `position`, else fetcher's epoch initial `{2024-01-01, id:0}`) → `fetchBatch(source, {date,id}, limit)` → `extractNextCursorData(lastItem)` → hand `events` to the consumer → ONLY after successful consumption does the caller `commitCursor` (upsert encoded string) → next cycle resumes from the committed point.
**Invariant:** FOUR must-not-break properties. (1) **Composite key, not timestamp alone**: the query filters `resultCreatedAt >= cursor.date AND resultId > cursor.id` sorted `+result_created_at` — rows sharing one timestamp are ordered/tie-broken by id, so a pure-timestamp cursor would skip or re-deliver them. (2) **Opaque-string persistence, validated decode**: the DB never interprets `position`; decode is total (throws loudly on corruption instead of silently restarting from epoch and re-emitting history). (3) **Fetch/commit separation** = at-least-once delivery: a crash between fetch and commit replays the last batch; consumers MUST be idempotent — committing before consumption would be at-most-once and lose events. (4) Empty batch ⇒ `extractNextCursorData(undefined)` returns `null` ⇒ nothing committed ⇒ the same cursor is retried later.
**Probe:** no upstream tests ship in the dist extract — coverage caveat recorded; deterministic source probes (anchored at `lh-basis/core/local-source/dist/Analytics/Cursors/Codecs`): `grep -c padStart TimestampBigIntCodec.js` = 1 (zero-padded id), decode guard present (`Invalid cursor format`), `analytics_cursor` schema carries `li_account_id`+`name` both UNIQUE, `InviteAcceptedDataFetcher.getInitialCursorValue` epoch `2024-01-01T00:00:00.000Z`. Fetcher twins prove the contract is a family: `MessageReplyRecievedDataFetcher` (file misspells "Recieved") flatMaps `messagesInfo` (one result → MANY message events, each still carrying `resultId`/`resultCreatedAt` for cursor continuity, `Boolean(messagesInfo)` filter dropping unpopulated rows) while `InviteAcceptedDataFetcher` adds a SEMANTIC pre-filter independent of the resume cursor (`collectingItemsProps.people.connectedAt >= epoch`) and maps one result → one event.

## Get live surrounding code
**Retrieve:**
```ts
// BM25/semantic search_graph return 0 for this plane (outside indexed roots — recorded caveat).
// Read the decisive sources directly instead:
await mcp.codebase_memory.check_index_coverage({ project: "lh-basis-source", paths: ["Analytics"] });
// source paths (absolute): <root>/core/local-source/dist/Analytics/{Cursors/Codecs/TimestampBigIntCodec.js,
//   Cursors/Codecs/CursorCodec.js, AnalyticsCursorRepo.js, Providers/EventsBatchProvider.js,
//   DataFetchers/MessageReplyRecievedDataFetcher.js, DataFetchers/InviteAcceptedDataFetcher.js}
```

## Verdict
Adopt the pattern: composite `(timestamp, id)` cursors with zero-padded encoding, opaque-string persistence with loud validated decode, one cursor row per (account, channel), fetch/consume/commit ordering for at-least-once semantics, epoch defaults per channel. Adapt the codec alphabet (epoch/base64/ULID), the storage backend (SQLite/Postgres upsert), and the fetcher interface names to host. Omit the vendored code itself — no-license source, patterns only; do not copy `TimestampBigIntCodec` or `EventsBatchProvider` code verbatim into any foundation or product.
