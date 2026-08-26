<!-- capsule-v2 -->
# HostedMetadataManager debounced usage pushes — how do per-doc updatedAt/usage writes coalesce into rare home-DB updates without losing the last change on shutdown?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the debounce/close contract that guarantees pending metadata reaches the database exactly once even when close races an in-flight push?

## Merge-into-pending + delay-relative-to-last-push + close() performs one final flush
**Path/Symbol:** `app/server/lib/HostedMetadataManager.ts` — whole class (:11–143): `scheduleUpdate` (:61–70), `_update` (:79–99), `_schedulePush` (:123–129), `_setOrUpdateMetadata` (:134–142), `close()` (:41–51).
**Signature:** `scheduleUpdate(docId: string, metadata: DocumentMetadata, minimizeDelay = false): void`; `close(): Promise<void>`; ctor takes `(saveDocsMetadata, minPushDelay = 60 /* seconds */)` → `_minPushDelayMs`.
**Data Shape:** Pending map `{ [docId]: DocumentMetadata }`; only two fields matter — `updatedAt` and `usage` (`usage !== undefined` gate :140). Single in-flight latch `_push: Promise<void> | null`; single timer `_timeout`.

### Decisive source
```ts
// HostedMetadataManager.ts:41-51 — close() = stop scheduling, await in-flight, ONE final flush if dirty
this._closing = true;
if (this._push) { await this._push; }
if (this._timeout) {
  this._update();                       // a scheduled push means there IS unpushed data
  if (this._push) { await this._push; }
}
```
```ts
// :123-128 — delay is measured from the LAST PUSH, not from schedule time
if (delayMs === undefined) {
  delayMs = Math.round(this._minPushDelayMs - (Date.now() - this._lastPushTime));
}
if (this._timeout) { clearTimeout(this._timeout); }
this._timeout = setTimeout(() => this._update(), delayMs < 0 ? 0 : delayMs);
```

**Flow:** every `scheduleUpdate` merges into the pending map FIRST (later metadata overwrites field-wise; first-write fields kept when later ones omit them) → early-return if a push is already scheduled and `minimizeDelay` is false → otherwise (re)schedule. `_update()` clears the timer, no-ops if a push is in flight, swaps-and-clears the map, stamps `_lastPushTime`, awaits the DB write; on completion, if NOT closing and new metadata arrived during the write with NO timer set (the minimize-delay storm case documented at :91–97), it self-reschedules at 0ms.
**Invariant:** At-most-one timer AND at-most-one in-flight promise at any moment; correctness rests on "metadata updated even if an update is already scheduled" (:64–66 comment) — coalescing happens in the MAP, never by dropping scheduleUpdate calls. `close()` must be idempotent-safe against double scheduling because `_closing` gates all future schedules while still permitting the final flush.
**Probe:** `test/server/lib/HostedMetadataManager.ts` (:46 "can throttle push calls", :93 "allows minimizing push delay when scheduling updates", :129 "allows calling close to force send pending requests"). Source pins: `grep -n 'minimizeDelay' app/server/lib/HostedMetadataManager.ts` (5 sites); `grep -c 'minPushDelay: number = 60' app/server/lib/HostedMetadataManager.ts` = 1.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"HostedMetadataManager scheduleUpdate saveDocsMetadata usage updatedAt","limit":10,"detail":"ids"}'
```

## Verdict
Adopt merge-into-pending coalescing, last-push-relative delays, minimizeDelay override for latency-sensitive callers, and the close-flush contract; adapt the persisted field pair to your metadata shape; omit grist's DocumentMetadata typing. Direct mocha coverage at this pin; runner-blocked locally — probes recorded as source-pinned assertions.
