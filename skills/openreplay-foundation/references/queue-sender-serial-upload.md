<!-- capsule-v2 -->
# QueueSender serial send queue — how does a WebWorker deliver batches over flaky fetch with bounded retries, keepalive budgeting, and a single-file queue?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** How do you serialize batch uploads from a worker so only one request is in flight, failures back off without losing order, and the browser's 64 KB keepalive cap never throws?

## QueueSender push/authorise/retry/sendBatch/clean
**Path/Symbol:** `tracker/tracker/src/webworker/QueueSender.ts:push` (:55-67), `authorise` (:47-53), `retry` (:84-96), `sendBatch` (:99-169), `clean` (:181-188).
**Signature:** `push(batch: Uint8Array, dataType = 'player'): void`; private `sendBatch(batch, isCompressed?, batchNum?, dataType): void`; constructor takes `MAX_ATTEMPTS_COUNT=10`, `ATTEMPT_TIMEOUT=250`, optional `onCompress`.
**Data Shape:** `QueueEntry {batch, dataType}` FIFO; `busy` latch (one in-flight send); `attemptsCount` retry counter reset on any success; `lastBatchNum` monotonic per-batch id surfaced in the URL query; `inflightKeepaliveBytes` running total of keepalive:true bytes.

### Decisive source
```ts
private retry(batch: Uint8Array, ...): void {
    if (this.attemptsCount >= this.MAX_ATTEMPTS_COUNT) {
      this.onFailure(`Failed to send batch after ${this.attemptsCount} attempts.`)
      return                                  // remains busy === true: terminal stall
    }
    this.attemptsCount++
    const batchCopy = new Uint8Array(batch)   // defensive copy before async gap
    setTimeout(() => this.sendBatch(batchCopy, ...), this.ATTEMPT_TIMEOUT * this.attemptsCount)
}
```
```ts
const useKeepalive =
    batch.length < KEEPALIVE_SIZE_LIMIT &&                       // 64 << 10
    this.inflightKeepaliveBytes + batch.length <= KEEPALIVE_SIZE_LIMIT
if (useKeepalive) this.inflightKeepaliveBytes += batch.length
// releaseKeepalive() in both .then and .catch
```

**Flow:** push → if idle+authorized start sending else enqueue → sendBatch POSTs raw bytes to `<ingestPoint>/v1/web/i?batch=<pageNo>_<batchNum>&keepalive=yes|no` with `Authorization` + `DataType` headers (+`Content-Encoding: gzip` when compressed) → 401 stops everything and calls onUnauthorised (session restart upstream); ≥400 or network reject → retry with LINEAR backoff `ATTEMPT_TIMEOUT * attemptsCount`; success resets attemptsCount and drains next. `r.body?.cancel()` discards response bodies immediately.
**Invariant:** Exactly one fetch is ever in flight (`busy` gates push and sendNext). Browsers cap total keepalive:true bytes at 64 KB per fetch group and fetch() THROWS SYNCHRONOUSLY past it — hence the client-side inflight ledger that downgrades to keepalive:false instead of crashing. Exhausted retries leave `busy === true` FOREVER by design: a dead sender must not silently drop queued batches; recovery happens via the worker-level restart (onFailure → initiateFailure → a_stop/a_start cycle). clean() sends the tail then nulls token+queue after 10 ms.
**Probe:** `grep -n 'ATTEMPT_TIMEOUT \* this.attemptsCount' tracker/tracker/src/webworker/QueueSender.ts` from repo root → line 94 (verified live); `grep -c 'inflightKeepaliveBytes' tracker/tracker/src/webworker/QueueSender.ts` → 4. Direct tests: `npx jest src/webworker/QueueSender.unit.test.ts` in `tracker/tracker` → 7/7 green.
**Retrieve:** search_graph project openreplay query "QueueSender retry attemptsCount backoff" → rank-1 `QueueSender.retry :84-96` line-exact at pin.

## Verdict
Adopt single-flight queue + linear-backoff copy-before-retry + keepalive byte ledger + terminal-stall-on-exhaustion as pure transport behavior; adapt endpoint paths/header sets to your ingest API; omit OpenReplay's compression handoff protocol if your worker compresses inline.
