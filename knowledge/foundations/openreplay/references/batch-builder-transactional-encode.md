<!-- capsule-v2 -->
# BatchBuilder transactional encode — how does a fixed-size encoder accept or reject a whole message atomically without corrupting prior bytes?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** When encoding a message into a bounded buffer can overflow mid-write, how do you guarantee a failed push leaves the builder byte-identical and reusable?

## BatchBuilder.push / flush / reset
**Path/Symbol:** `tracker/tracker/src/webworker/BatchBuilder.ts:push` (:40-82), `flush` (:90-100), `reset` (:102-108), `writeHeader` (:110-130), `writeMessageWithSize` (:134-149).
**Signature:** `push(msg: Message, ctx: BatchContext): boolean`; `flush(): Uint8Array | null`; private `writeMessageWithSize(msg: Message): boolean`.
**Data Shape:** `BatchContext = {pageNo, index, timestamp, url, tabId}`; internal `Snapshot` freezes the first message's ctx as batch metadata; `hasNonTimestamp` flag distinguishes real content from header-only state; `lastPushedTs` tracks the last timestamp written for dedup.

### Decisive source
```ts
push(msg: Message, ctx: BatchContext): boolean {
    const e = this.encoder
    const wasFresh = this.snap === null
    const savedOffset = e.getCurrentOffset()
    const savedCp = e.getCurrentCheckpoint()
    ...
    if (!this.writeMessageWithSize(msg)) {
      e.rewind(savedOffset, savedCp)          // undo partial bytes
      if (wasFresh) this.snap = null           // fresh batch that failed = no batch
      return false
    }
```
```ts
private writeMessageWithSize(msg: Message): boolean {
    if (!e.uint(msg[0]) || !e.skip(SIZE_BYTES)) return false   // reserve 3-byte size slot
    const startOffset = e.getCurrentOffset()
    if (!e.encode(msg)) return false
    const size = e.getCurrentOffset() - startOffset
    if (size > MAX_M_SIZE) { console.warn(...); return false } // cannot back-patch >16MB
    if (endOffset > this.bufferSize) return false              // soft budget
    this.writeSizeAt(size, startOffset - SIZE_BYTES)           // back-patch LE size
    e.checkpoint()
    return true
}
```

**Flow:** capture offset+checkpoint BEFORE any write → on first push of a batch, write header (BatchMetadata without size prefix, then Timestamp + TabData WITH prefixes) → auto-synthesize `[Type.Timestamp, ctx.timestamp]` before any non-Timestamp message whose ts advanced since last push (skipped when msg IS a Timestamp — no duplicates) → attempt message write → any failure rewinds BOTH offset and checkpoint and restores snapshot state → caller retries later or routes elsewhere.
**Invariant:** A failed push is fully invisible: offset, checkpoint, snap, and lastPushedTs all roll back, so retrying the same message later produces identical bytes. `MAX_M_SIZE = (1<<24)-1` exists because the 3-byte size slot is back-patched after encoding — a larger payload physically cannot be prefixed retroactively, hence warn-and-refuse. `hasContent()` requires `snap !== null && hasNonTimestamp`, so flushing an empty/timestamps-only builder returns null and never emits a wire frame.
**Probe:** `grep -c 'rewind' tracker/tracker/src/webworker/BatchBuilder.ts` from repo root → **4** (verified live); direct tests: `npx jest src/tests/batchBuilder.unit.test.ts` in `tracker/tracker` → 16/16 green incl. "push that fails mid-batch only rolls back its own bytes" and "after a failed first push, ctx of the next push wins".
**Retrieve:** search_graph project openreplay query "BatchBuilder push flush" → rank-1 Method nodes `BatchBuilder.push :40-82`, `flush :90-100` line-exact at pin.

## Verdict
Adopt save-offset/checkpoint → write → rewind-on-fail as the canonical transactional encoder pattern plus reserve-slot-then-backpatch sizing; adapt the concrete varint/zigzag field encodings to your codec; omit OpenReplay-specific message type IDs (they are protocol-versioned constants).
