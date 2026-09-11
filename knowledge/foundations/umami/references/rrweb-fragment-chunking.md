<!-- capsule-v2 -->
# rrweb chunking with binary-search fragmentation — how do you stream full-DOM snapshots through size-limited POSTs and reassemble them server-side?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are oversized replay events split, sequenced, and restored — including the monotone chunk clock?

## rrweb-fragment-chunking
**Path/Symbol:** sender `src/recorder/index.js:getReplayEventFragments :139-181, sendReplayEvents :196-241, getReplayChunkIndex :78-83`; reassembler `src/lib/replay.ts:isReplayEventFragment :19-31, restoreReplayEventFragments :47-103`; direct test `src/lib/replay.test.ts:85-121`.
**Signature:** fragment `{type:'umami:rrweb-event-fragment', data:{id,index,total,value}}`; REPLAY_MAX_PAYLOAD_SIZE=500000; placeholder total=999999999 during sizing.
**Data Shape:** chunk timestamp = base second + per-chunk offset (`timestamp + chunkOffset`) so server-side ordering is total without a sequence column.

### Decisive source
```js
while (start < value.length) {                 // binary-search the largest prefix that fits
  let low = start + 1, high = value.length, end = start;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const fragment = createReplayFragment(id, fragments.length,
                      REPLAY_FRAGMENT_TOTAL_PLACEHOLDER, eventTimestamp, value.slice(start, mid));
    if (isReplayPayloadTooLarge([fragment], ...)) high = mid - 1; else { end = mid; low = mid + 1; }
  }
  if (end === start) end = start + 1;          // pathological 1-char progress guarantee
  fragments.push(value.slice(start, end)); start = end;
}
// restore: values Map keyed by index; complete when received === total → JSON.parse(concat)
```

**Flow:** full snapshots flush buffers first and travel alone (possibly fragmented) → incremental events accumulate until count(100)/interval(2s)/size(500KB) → each fragment gets monotone timestamps → server `restoreReplayEventFragments` reassembles in stream order; malformed groups are DROPPED, never fatal.
**Invariant:** index/total live in every fragment so out-of-order arrival reassembles idempotently (duplicate indexes ignored via `values.has(index)`); the placeholder-total trick exists because you can't know `total` until sizing completes — the validator must accept it only during capture, never on the wire from clients. Partial replay beats failed response: catch-and-skip is deliberate.
**Probe:** `grep -n "restores fragmented events" src/lib/replay.test.ts` → :85 (2-fragment restore to exact deep-equal) and `grep -n "counts a fragment group as one event" src/lib/replay.test.ts` → :122. Sender pins: `grep -n "999999999" src/recorder/index.js` → :28.
**Probe:** `grep -c "REPLAY_FRAGMENT_TOTAL_PLACEHOLDER" src/recorder/index.js` → ≥3 lines.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "getReplayEventFragments restoreReplayEventFragments binary", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt sized-chunk fragmentation + id-keyed reassembly for any large-payload-over-small-pipes transport (replays, logs, crash dumps); adapt size limits; omit keepalive-vs-fetch fallbacks if payloads smaller.
