<!-- capsule-v2 -->
# streaming-part-upload-economics — How do you stream chunks into S3 multipart parts while recording, without exhausting memory or blocking the recorder?

**Source:** cap AGPL-3.0 `main@0ce9e67516b14449c4263c0b173c85c40f30421b`; Codebase Memory `ext-cap`. **Question:** What are the buffering thresholds, concurrency limits, overflow guard, and the offline-retry wait that keeps a network blip from killing a recording?

## 5MiB min part; 3 parallel slots (1 for Drive); 128MiB pending-bytes guard = fatal; every retry waits for navigator.onLine with a 60s cap
**Path/Symbol:** `packages/recorder-core/src/instant-mp4-uploader.ts:3-23` (constants), buffer→part assembly `:460-542` (`handleChunk`/`flushBuffer`/`takeBufferedPart`), slots `:616-638`, retry+online-wait `:652-738`, finalize drain `:958-1024`.
**Signature:** `handleChunk(blob: Blob, recordedTotalBytes: number)`; `private enqueueUpload(part: Blob)` throws the overflow error; `finalize(options)` drains before completing.
**Data Shape:** `MIN_PART_SIZE_BYTES = 5MiB`; `MAX_PARALLEL_PART_UPLOADS = 3`; `MAX_PENDING_UPLOAD_BYTES = 128MiB`; attempts 8 × base 500ms → max 30s; XHR stall timeout 30s of NO progress events; request timeout 5min; Drive: 16MiB aligned parts + Content-Range resumable headers, single slot.

### Decisive source
```ts
// Offline failures are near-instant, so without this wait a brief
// connectivity drop would burn every attempt in a few seconds and
// kill the recording while plenty of buffer headroom remains.
await this.waitForRetryDelay(Math.min(PART_RETRY_MAX_DELAY_MS, PART_RETRY_BASE_DELAY_MS * 2 ** (attempt - 1)));
await this.waitForOnline();   // 'online' event OR 60s cap
```

**Flow:** Chunks accumulate until ≥5MiB then flush as one part; parts enqueue immediately (partNumbers strictly increasing, offsets tracked for Drive). Each part acquires one of N slots (waiters queue FIFO), presigns, PUTs via XHR with per-progress-event stall refresh. Overflow check happens at ENQUEUE: pending+part > 128MiB ⇒ markFatalError("Upload could not keep up with recording") — recording stops by design rather than growing unbounded. Finalize first drains in-flight when tail flush would trip the guard, flushes force, uploads a whole final blob in 16MiB slices only when zero parts exist, sorts parts by number into complete.
**Invariant:** Retry waits must be ONLINE-GATED, not just timed — near-instant offline failures otherwise burn all 8 attempts in seconds. Slot release hands directly to a waiter (no double-increment past the provider cap). Cancel aborts in-flight XHRs, cancels retry waits/timers, and aborts server-side AFTER draining.
**Probe:** `packages/recorder-core/__tests__/instant-recording-uploader.test.ts` — `retries a failed part upload before completing` (:438), `retries a stalled part upload before completing` (:490), `surfaces upload overflow before multipart completion` (:711), `uploads large finalized blobs in multiple parts without hitting live overflow limits` (:738), `cancels cleanly while waiting to retry a failed part upload` (:888).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cap", query: "InstantRecordingUploader enqueueUpload waitForOnline", limit: 10 });
```

## Verdict
Adopt thresholds, slot semaphore, online-gated backoff, and enqueue-time overflow fatality. Adapt provider dialects (Drive Content-Range) to your storage targets.
