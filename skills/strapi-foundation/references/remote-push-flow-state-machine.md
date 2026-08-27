<!-- capsule-v2 -->
# Remote push flow state machine — how do you keep a long-running WS transfer protocol ordered and single-stage?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** A push transfer arrives as an untrusted sequence of `start`/`stream`/`end` step messages over a WebSocket; how do you enforce stage order, exactly-one-stage-at-a-time, and per-asset stream integrity on the receiving side?

## Flow state machine seam
**Path/Symbol:** `packages/core/data-transfer/src/strapi/remote/flows/index.ts:createFlow` (21–84) + `Step` type (3–6); `packages/core/data-transfer/src/strapi/remote/flows/default.ts` (whole, 20 lines); `packages/core/data-transfer/src/strapi/remote/handlers/push.ts:lockTransferStep` (295–312), `unlockTransferStep` (314–333), `assertValidStreamTransferStep` (193–208), `onTransferStep` (335–409), `streamAsset` (434–526), `init` (528–574).
**Signature:** `createFlow(flow: readonly Step[]): TransferFlow` with `has/can/cannot/set/get`; `Step = {kind:'action', action:string} | {kind:'transfer', stage:TransferStage, locked?:boolean}`.
**Data Shape:** default flow = `[bootstrap, init, beforeTransfer, schemas, entities, assets, links, configuration, close]`. Handler keeps per-connection registries: `streams[stage]` (one Writable per active stage), `assets[assetID]` (IAsset + PassThrough), `assetChecksums[assetID]` (sha256 Hash), `stats[stage] = {started, finished}`.

### Decisive source
```ts
// flows/index.ts — ordering is INDEX DIFFERENCE in the declared flow; same transfer step may repeat
const indexesDifference = findStepIndex(step) - findStepIndex(state.step);
// It's possible to send multiple time the same transfer step in a row
if (indexesDifference === 0 && step.kind === 'transfer') { return true; }
return indexesDifference > 0;
```
```ts
// push.ts lockTransferStep — one locked stage at a time, no out-of-order starts
if (currentStep?.kind === 'transfer' && currentStep.locked) {
  throw new ProviderTransferError(
    `It's not possible to start a new transfer stage (${stage}) while another one is in progress (${currentStep.stage})`);
}
if (this.flow?.cannot(nextStep)) { throw ... }
this.flow?.set({ ...nextStep, locked: true });
```
```ts
// onTransferStep 'stream' — objects are written SEQUENTIALLY with awaited writes (no overlap)
for (const item of msg.data) {
  this.stats[stage].started += 1;
  await write(stream, item);
  this.stats[stage].finished += 1;
}
```
```ts
// streamAsset 'end' — checksum verified BEFORE the asset's PassThrough is closed
const checksum = this.assetChecksums?.[assetID]?.digest('hex');
if (!checksum || checksum !== item.checksum.value) {
  throw new ProviderTransferError(`Checksum mismatch for asset "${assetID}" (expected ${item.checksum.value}, got ${checksum ?? 'none'})`);
}
...
assetStream.on('close', () => { this.stats.assets.finished += 1; delete this.assets[assetID]; resolve(); }).on('error', reject).end();
```

**Flow:** `init` command creates the flow (`createFlow(DEFAULT_TRANSFER_FLOW)`), the local destination provider, fresh stats/checksum registries, and negotiates `checksums` + `assetEncoding` by echoing them back → action messages (`bootstrap`, `beforeTransfer`, `close`, ...) advance the flow only if `flow.can(step)` → step `start`: `lockTransferStep` (refuses while another stage is locked or out of order) + create the stage Writable + zero its stats (+ a 5s memory-sampling interval for assets) → step `stream`: `assertValidStreamTransferStep` requires the current step to be this unlocked-or-absent stage, then awaited sequential writes into the stage Writable; assets route through `streamAsset` which maintains per-asset PassThroughs (`start` registers + writes the row, `stream` appends decoded chunks to the sha256 hash and the PassThrough, `end` verifies the checksum, closes the PassThrough, deletes the registry entry only on close) → step `end`: `unlockTransferStep` (requires the stage to be locked), awaits the Writable's close event, deletes the registry entry, returns `{ok, stats}`.
**Invariant:** at most ONE transfer stage is locked at any moment, and a stage cannot be started out of declared order (index difference must be > 0); repeated `stream` messages for the SAME stage are legal (index difference 0 is allowed only for transfer steps) but every other repeat is rejected; `end` without a matching `start` throws ("You need to initialize the transfer stage before ending it"); asset chunks for an unknown assetID throw instead of being dropped; the checksum is verified before the asset stream is ended so a corrupt asset never reaches the destination writer; writes are awaited one-by-one so the destination's backpressure is never bypassed by batch overlap.
**Probe:** no direct unit test exists for the server-side flow machine (recorded coverage caveat); the protocol it implements is pinned client-side by `src/strapi/providers/remote-destination/__tests__/push-assets-write-stream.test.ts` (start/stream/end message shapes, 1MiB flush-before-complete batching), `checksum-negotiation.test.ts` (whole: peer without checksum support ⇒ warning + end item WITHOUT checksum field), and `asset-encoding-negotiation.test.ts` (non-echoing remote ⇒ legacy chunk shape fallback).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "lockTransferStep unlockTransferStep createFlow can cannot", file_pattern: "packages/core/data-transfer/src/strapi/remote/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 4 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the index-difference flow kernel (declare the legal order once as a readonly Step list; `can` = forward-only with same-step repetition for streaming steps) plus the lock/unlock single-stage invariant — together they turn an unordered message channel into a resumable ordered protocol. Adopt the per-asset registry keyed by ID with checksum-before-close. Adapt the step list, the memory-sampling interval, and the stats shape to your stages. Omit Strapi's provider instantiation inside `init` (the destination provider is host-specific) and the koa/ws wiring (see ws-uuid-replay-dispatch). Coverage caveat: server-side flow behavior has NO direct unit test in the checkout; the client-side remote-destination tests pin the wire contract it serves.
