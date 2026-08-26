<!-- capsule-v2 -->
# Main-thread gzip offload — where does compression happen when the worker can't or shouldn't gzip a batch?

**Source:** OpenReplay AGPL-3.0 (tracker MIT) `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** How do main thread and web worker split compression duty without ever blocking or losing a batch?

## handleWorkerMsg 'compress' branch → CompressionStream → compressed|uncompressed reply
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts:handleWorkerMsg` (:846–902, compress :867–890); threshold default (:261), server-adopted (:1663); worker-side consumer `QueueSender.onCompress`/`sendCompressed` (`tracker/tracker/src/webworker/QueueSender.ts`).
**Signature:** `private handleWorkerMsg(data: FromWorkerData)`; compress envelope `{type:'compress', batch: ArrayBuffer, dataType}` → replies `{type:'compressed', batch: Uint8Array, dataType}` | `{type:'uncompressed', batch, dataType}`.
**Data Shape:** `compressionThreshold = 24 * 1000` bytes (constructor default, overwritten by the admission response's `compressionThreshold`); capability probe `'CompressionStream' in globalThis`.

### Decisive source
```ts
} else if (data.type === 'compress') {
  const batch = data.batch
  const batchSize = batch.byteLength
  const hasCompressionAPI = 'CompressionStream' in globalThis
  if (batchSize > this.compressionThreshold && hasCompressionAPI) {
    const blob = new Blob([batch as BlobPart])
    new Response(blob.stream().pipeThrough(new CompressionStream('gzip')))
      .arrayBuffer()
      .then((compressedBuffer) => {
        this.worker?.postMessage({ type: 'compressed', batch: new Uint8Array(compressedBuffer), dataType })
      })
      .catch((err) => {
        this.debug.error('Openreplay compression error:', err)
        this.worker?.postMessage({ type: 'uncompressed', batch: batch, dataType })  // fail-open
      })
  } else {
    this.worker?.postMessage({ type: 'uncompressed', batch: batch, dataType })
  }
}
```

Sibling dispatch arms in the same handler: `'local_save'` (Blob → objectURL → synthetic `<a download>` click → revokeObjectURL — the debug artifact dump), `'queue_empty'` → `onSessionSent()` (offline-upload completion latch), and the restart strings `data==='a_stop'|'a_start'|'not_init'` / `{type:'failure'}` (main side of the worker FSM).
**Flow:** the WORKER decides a batch is worth compressing (it owns BatchWriter sizes) but delegates the CPU-heavy gzip to the MAIN thread, which owns `CompressionStream`; the reply is asymmetric by design — 'compressed' only after a successful pipeThrough, 'uncompressed' on ANY error, undersized batch, or missing API. The worker's QueueSender then sends with `Content-Encoding: gzip` when it receives the compressed payload.
**Invariant:** Compression is best-effort and fail-open: no error path drops a batch — worst case it ships uncompressed. Threshold is SERVER-controlled (adopted from `/v1/web/start` at :1663), so the backend tunes wire format per project. The capability probe means old browsers silently take the uncompressed path instead of crashing.
**Probe:** `grep -n 'CompressionStream' tracker/tracker/src/main/app/index.ts` → :871, :874; `grep -n '24 \* 1000' …/app/index.ts` → :261 (verified live at pin).
**Direct test:** worker-side half pinned by `tracker/tracker/src/webworker/QueueSender.unit.test.ts` ("Sends compressed request if onCompress is provided…", :64–81 asserts `Content-Encoding: gzip`) — suite executed green at this pin (PASS, part of 18/18). The main-thread 'compress' branch itself has no dedicated suite.

## Get live surrounding code
**Retrieve (executed):**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "handleWorkerMsg compress CompressionStream uncompressed batch", limit: 6 });
```
→ rank-1 `App.handleWorkerMsg :846-902`, rank-2 `QueueSender.sendUncompressed :176-179`, plus `QueueSender.unit.test.ts onCompress :65`.

## Verdict
Adopt threshold-gated, capability-probed, fail-open compression offload across a worker boundary as pure behavior. Adapt the transport envelope to your RPC channel. Omit local_save artifact dumping unless you need wire debugging.
