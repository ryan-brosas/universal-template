<!-- capsule-v2 -->
# Canvas frame packing + upload queue — how are periodic canvas snapshots batched, capped, and shipped?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What is the binary frame format and the queueing/backpressure a porter must reproduce for canvas recording?

## [u64 LE ts][u32 LE size][bytes] × N, 10-frame batches, queue cap 50
**Path/Symbol:** `tracker/tracker/src/main/app/canvas.ts` — `packFrames` (:415–449), `captureSnapshot` quality/scaling (:384–413), record loop (:125–197: `images.length > 9` flush, IntersectionObserver pause, `useAnimationFrame` option), `sendSnaps/processUploadQueue/uploadBatch` (:198–312: `MAX_QUEUE_SIZE=50`, `MAX_CONCURRENT_UPLOADS=2`, endpoint `/v1/web/images`), `clear()` flush-before-cleanup (:358–381).
**Signature:** `packFrames(images): Promise<ArrayBuffer | null>`; `captureSnapshot(canvas, quality, dummy, fixedScaling, fileExt, onBlob)`.
**Data Shape:** per frame: uint64 LE timestamp + uint32 LE byteLength + payload; totalSize = Σ(8+4+len). Quality map low .35 / medium .55 / high .8; formats webp|png|jpeg|avif; fixedScaling divides by devicePixelRatio.

### Decisive source
```ts
view.setUint32(offset, ts % 0x100000000, true)          // ts low word
view.setUint32(offset + 4, Math.floor(ts / 0x100000000), true)
offset += 8
view.setUint32(offset, ab.byteLength, true)             // size
...
this.snapshots[id].images.push({ id: this.app.timestamp(), data: blob })
if (this.snapshots[id].images.length > 9) { this.sendSnaps(...); this.snapshots[id].images = [] }
```

**Flow:** interval (1000/fps) → if visible & idle capture via toBlob (dummy canvas downscale for HI-DPI) → every 10 frames enqueue → upload loop drains with max-2 concurrent POSTs (FormData `type=frames`) → stop clears but first FLUSHES pending images so the session tail isn't lost.
**Invariant:** Queue overflow drops the NEW batch loudly (`Upload queue full`), never blocks the ticker. `isCapturing` latch prevents overlapping async toBlob of the same canvas. Pause-on-offscreen saves bandwidth (IntersectionObserver).
**Probe:** `grep -c 'totalSize += 8 + 4 + ab.byteLength' tracker/tracker/src/main/app/canvas.ts` → `2`; `grep -c 'images.length > 9' tracker/tracker/src/main/app/canvas.ts` → `1`; `grep -c 'MAX_CONCURRENT_UPLOADS = 2' tracker/tracker/src/main/app/canvas.ts` → `1`; direct tests `tests/canvas.test.ts` executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "packFrames captureSnapshot sendSnaps MAX_QUEUE_SIZE", limit: 10 });
```

## Verdict
Adopt framed u64/u32 packing + bounded queue. Adapt fps/quality to product. Omit debug local-save branch.
