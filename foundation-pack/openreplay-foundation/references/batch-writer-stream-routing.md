<!-- capsule-v2 -->
# BatchWriter stream routing & soft-budget ladder — how do four parallel batch streams share one message firehose without a single oversized message wedging the session?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** When messages must be split into player/assets/devtools/analytics streams with per-batch size budgets, what is the escalation path for a message that does not fit?

## BatchWriter routeMessage / pushTo / finaliseBatch
**Path/Symbol:** `tracker/tracker/src/webworker/BatchWriter.ts:routeMessage` (:81-89), `pushTo` (:91-114), `writeMessage` (:65-79), `finaliseBatch` (:130-135), `setProtocolVersion` (:56-63).
**Signature:** `writeMessage(message: Message): void`; private `routeMessage(message: Message): BatchBuilder`; private `pushTo(builder: BatchBuilder, message: Message): void`.
**Data Shape:** Four BatchBuilders (player v1/v2, assets ASSETS_VERSION=3, devtools=4, analytics=5); `beaconSize = 2e5` soft budget per builder, `beaconSizeLimit = 1e6` hard cap (server-overridable via auth msg `beaconSizeLimit`); `nextIndex` becomes BatchMetadata.firstIndex and increments ONLY on accepted pushes.

### Decisive source
```ts
private pushTo(builder: BatchBuilder, message: Message): void {
    const ctx = this.currentCtx()          // identical across retries by construction
    if (builder.push(message, ctx)) { this.nextIndex++; return }
    // Soft-budget hit: flush this stream's batch, retry once on the same builder.
    this.flushBuilder(builder)
    if (builder.push(message, ctx)) { this.nextIndex++; return }
    // Single message exceeds soft budget: build a one-shot oversized batch.
    const big = new BatchBuilder(this.beaconSizeLimit, builder.version, builder.dataType)
    if (!big.push(message, ctx)) {
      console.warn('OpenReplay: beacon size overflow. Skipping large message.', message)
      return                                 // drop is FINAL; nextIndex not advanced
    }
    ...
}
```

**Flow:** writeMessage first intercepts control shapes — `[−1]` sentinel → finalise all batches + onOfflineEnd; Timestamp/SetPageLocation mutate writer state (this.timestamp/this.url) BEFORE routing so every subsequent batch header carries them → protocolVersion===2 routes by ASSET_MESSAGES/DEVTOOLS_MESSAGES/ANALYTICS_MESSAGES type sets, else everything goes to playerBuilder → pushTo three-rung ladder (fit / flush-then-retry / one-shot big builder at hard cap) → finaliseBatch flushes all four in fixed order.
**Invariant:** The retry context is IDENTICAL across attempts because `nextIndex` advances only on success and timestamp/url are mutated before pushTo — a flushed-then-retried message keeps its original index/ts/url. A message that exceeds even beaconSizeLimit is dropped with a warning rather than blocking the pipeline; index never counts dropped messages. setProtocolVersion resets+recreates ONLY the player builder (version is baked into builder constructor).
**Probe:** `grep -n 'ASSETS_VERSION\|DEVTOOLS_VERSION\|ANALYTICS_VERSION' tracker/tracker/src/webworker/BatchWriter.ts | head -3` from repo root → lines 7,8,9 = 3,4,5 (verified live); direct tests: `npx jest src/tests/batchWriter.unit.test.ts src/tests/batchWriter_regressions.test.ts` in `tracker/tracker` → 22+7 green incl. "every batch (normal + warn branch + oversized) carries the full prelude".
**Retrieve:** search_graph project openreplay query "startSessionHandlerWeb pushMessagesHandlerWeb beacon" → rank-1 server twins + `NewBeaconCache :19-27` neighbors; own-project query "BatchWriter protocolVersion" resolves Method nodes in BatchWriter.ts.

## Verdict
Adopt the per-stream builders + fit/flush-retry/one-shot escalation and success-gated index advancement as pure batching behavior; adapt DataType sets to your message taxonomy; omit canvas/devtools product-specific version constants beyond the pattern.
