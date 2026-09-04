<!-- capsule-v2 -->
# Progress reporting plane — how do you report per-stage count/bytes/ETA without consuming or buffering the data streams?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** A streaming transfer must expose live progress (records, bytes, per-key aggregates, totals for ETA) to a UI; how do you measure the stream without reading it twice, breaking backpressure, or holding the payload in memory?

## Progress-tracker seam
**Path/Symbol:** `packages/core/data-transfer/src/engine/index.ts:#updateTransferProgress` (269–311), `#progressTracker` (314–333), `#progressTrackerChunks` (338–415), `#emitTransferUpdate` (418–420), `#emitStageUpdate` (425–437), `#mergeSourceStageTotals` (1017–1039); types `packages/core/data-transfer/src/types/utils.ts:StageProgress` (76–91), `TransferProgress` (93–95), `StageTotalsEstimate` (67–70); source-side estimator `packages/core/data-transfer/src/strapi/providers/local-source/estimate-asset-totals.ts:estimateAssetTotals` (whole file).
**Signature:** `#progressTracker(stage, aggregate?: {size?, key?}): PassThrough`; `#progressTrackerChunks(stage, aggregate?: {key?}): PassThrough`; `ISourceProvider.getStageTotals?(stage): MaybePromise<StageTotalsEstimate | null | undefined>`.
**Data Shape:** `progress.data[stage] = {count, bytes, startTime, endTime?, totalBytes?, totalCount?, aggregates?: {[key]: {count, bytes}}}`. Events on `progress.stream` (an object-mode PassThrough): `transfer::init|start|finish|error` and `stage::start|progress|finish|skip|error`, each stage event carrying `{data: progress.data, stage}` — the LIVE object, which mutates during the stage.

### Decisive source
```ts
// #progressTrackerChunks — assets: REPLACE asset.stream with a counting Transform so the
// destination keeps a single consumer (no double-consumption, backpressure preserved)
const progressTransform = new Transform({
  objectMode: true,
  transform(chunk: Buffer | unknown, _enc, cb) {
    const byteLength = Buffer.isBuffer(chunk) ? chunk.length : 1;
    stageProgress.bytes += byteLength;
    ...
    cb(null, chunk);
  },
  flush(cb) {
    stageProgress.count += 1;   // one count PER ASSET, incremented when its stream ends
    ...
    cb(null);
  },
});
asset.stream.on('error', (err: Error) => progressTransform.destroy(err));
asset.stream.pipe(progressTransform);
asset.stream = progressTransform;
```
```ts
// #updateTransferProgress — object stages: bytes default to serialized size
const size = aggregate?.size?.(data) ?? JSON.stringify(data).length;
...
if (key) { aggregates[key] ??= {count: 0, bytes: 0}; aggregates[key].count += 1; aggregates[key].bytes += size; }
```
```ts
// #mergeSourceStageTotals — source-estimated totals land BEFORE stage::start so the UI can show ETA
const totals = await getTotals.call(this.sourceProvider, stage);
if (!totals || (totals.totalBytes == null && totals.totalCount == null)) { return; }
if (totals.totalBytes != null) { stageProgress.totalBytes = totals.totalBytes; }
if (totals.totalCount != null) { stageProgress.totalCount = totals.totalCount; }
```

**Flow:** each stage builds `[source, transform?, tracker?, destination]`; the tracker is a PassThrough in the chain, so every object/chunk passes through it exactly once → object stages: per-object count+bytes (+optional per-key aggregate, key e.g. entity type or schema modelType) and a `stage::progress` emit per object → asset stages: the tracker swaps each asset's inner stream for a counting Transform (bytes per chunk, count in flush) so the destination consumes the replacement → before the assets stage starts, `#mergeSourceStageTotals` asks the source for `getStageTotals('assets')` and merges totalBytes/totalCount into the stage entry → `stage::start` fires AFTER the merge, so listeners see totals at start → `endTime` stamped in the stage's finally block.
**Invariant:** the tracker must never CONSUME the asset stream itself — it replaces `asset.stream` with a pipe-through Transform or the destination receives an already-drained (empty) stream; non-Buffer chunks count as exactly 1 byte (documented cosmetic rule, not an error); per-asset count increments in `flush`, not per chunk, so one asset = one record regardless of chunking; totals are merged before `stage::start` or the UI computes ETA against a zero denominator; events carry the live progress object, so consumers must snapshot if they need a stable view.
**Probe:** `packages/core/data-transfer/src/engine/__tests__/engine.test.ts` — 'destination receives full stream bytes for each asset (no double-consumption)' (1272–1330) pins exact byte counts per asset reaching the destination; 'progress byte totals: a non-Buffer chunk contributes 1' (1332–1360) pins the 1-byte rule; 'heap growth during asset transfer stays bounded' (1362–1393) pins streaming-not-buffering; 'merges source getStageTotals into assets progress before stage::start' (737–760) pins the pre-start merge with a snapshot of `{totalBytes: 12345, totalCount: 7, count: 0, bytes: 0}`; 'emits stage::progress events' (698–719) pins the exact chunk+flush event arithmetic (11 events for 9 chunks + 2 asset ends). Source-side estimator pinned by `src/strapi/providers/local-source/__tests__/estimate-asset-totals.test.ts` (DB-size fast path vs stat/HTTP fallback, ENOENT rows skipped like the stream does).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "progressTrackerChunks updateTransferProgress getStageTotals", file_pattern: "packages/core/data-transfer/src/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 4 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt both tracker shapes as the portable answer to "measure without consuming": per-object PassThrough for record stages, stream-replacing counting Transform for nested binary streams; the pre-start totals merge for ETA; and the live-object event contract with explicit snapshot guidance. Adapt the byte heuristic (`JSON.stringify(data).length`) to your payload sizes and the aggregate keys to your grouping needs. Omit Strapi's upload-plugin-specific estimation (local stat vs signed-URL HTTP fallback) — keep only the contract that the estimator must skip the same rows the stream skips (ENOENT parity). Coverage caveat: no unit test asserts the `aggregates` map directly; it is exercised indirectly by the per-key tracker wiring.
