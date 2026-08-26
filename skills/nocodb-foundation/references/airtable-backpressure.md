<!-- capsule-v2 -->
# Airtable backpressure streaming — how do you pull pages from a rate-limited remote API into bulk inserts so neither side outruns the other?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does readAllData pause upstream paging when downstream insert work piles up?

## counter-gated stream pause + PQueue resume
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/helpers/readAndProcessData.ts:readAllData` (31-108), `importData` consumer loop (110-336).
**Signature:** `readAllData({table, atBase, dataStream, counter, ...}): Promise<boolean>`; knobs `STREAM_BUFFER_LIMIT=100`, `QUEUE_BUFFER_LIMIT=20`, `BULK_DATA_BATCH_COUNT=10`, `BULK_DATA_BATCH_SIZE=20*1024` bytes (all env-tunable).
**Data Shape:** each record pushed as JSON string `{_atId, ...fields}`; shared mutable `counter.streamingCounter`.

### Decisive source
```ts
// producer: after each page of 100 records
if (counter && counter.streamingCounter >= STREAM_BUFFER_LIMIT) {
  await new Promise((resolve) => {
    const interval = setInterval(() => {
      if (counter.streamingCounter < STREAM_BUFFER_LIMIT / 2) {  // hysteresis
        clearInterval(interval); resolve(true);
      }
    }, 100);
  });
}
fetchNextPage();
// consumer: queue-depth gating around each task
if (queue.size >= QUEUE_BUFFER_LIMIT) dataStream.pause();
... inside task, after processing:
if (queue.size < QUEUE_BUFFER_LIMIT / 2) dataStream.resume();
```

**Flow:** Airtable `eachPage` pushes records onto a plain Readable and bumps the counter; if ≥100 unconsumed records it busy-waits (100 ms poll) until below 50 — pausing the REMOTE API rather than the stream. The consumer enqueues per-record transform+insert tasks; queue depth ≥20 pauses the Readable, resuming only under half. Batches flush on count≥10 AND byte-size≥20 KB.
**Invariant:** both gates use HYSTERESIS (pause at N, resume at N/2) to avoid resume-thrash. The producer's wait happens BEFORE fetchNextPage() — Airtable never sees unbounded demand. Byte-size check (`object-sizeof`) matters because Airtable rows vary wildly in width; count alone would let a few huge rows blow memory.
**Probe:** no unit test upstream; file is parse_partial in the graph (ranges 45-47/136-138/373-375) — claims verified by reading source directly. Source-grounded probe: `readAndProcessData.ts:79-93` — interval poll with `/2` threshold; `:246-258, 291-293` — pause/resume pair around queue.size.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "readAllData eachPage STREAM_BUFFER_LIMIT dataStream pause", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-level backpressure (remote-paging gate + local queue gate) with hysteresis and byte-aware batching; adapt API client, limits, and env names to host; omit Airtable `_atId` bookkeeping unless migrating from it. Coverage caveat: graph parse_partial — source read directly.
