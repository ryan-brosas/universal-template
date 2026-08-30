<!-- capsule-v2 -->
# Transfer-engine stage pipeline — how do you orchestrate multi-stage streaming transfers with skip, cancel, and rollback?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** A transfer moves several heterogeneous data kinds (schemas, entities, assets, links, configuration) between two providers that only expose read/write streams; how do you run them in a fixed order with per-stage skipping, mid-stage cancellation, and destination rollback on failure — without one giant transaction?

## Engine stage-pipeline seam
**Path/Symbol:** `packages/core/data-transfer/src/engine/index.ts:TransferEngine` (class, lines 88–1055); `transfer()` (819–868), `#transferStage` (590–681), `shouldSkipStage` (563–587), `abortTransfer` (683–687), `bootstrap` (705–719), `close` (721–735); `TRANSFER_STAGES` (51–57), `TransferGroupPresets` (64–84); provider contract `packages/core/data-transfer/src/types/providers.ts:ISourceProvider/IDestinationProvider` (whole file).
**Signature:** `createTransferEngine(sourceProvider: ISourceProvider, destinationProvider: IDestinationProvider, options: ITransferEngineOptions): TransferEngine`; `transfer(): Promise<ITransferResults<S,D>>`; per-stage `#transferStage({stage, source?, destination?, transform?, tracker?})`.
**Data Shape:** providers expose optional `create*ReadStream()`/`create*WriteStream()` pairs plus lifecycle hooks (`bootstrap`, `close`, `beforeTransfer`, `rollback(e)`, `getMetadata`, `getSchemas`). Options: `versionStrategy`, `schemaStrategy`, `transforms` (global + per-stage filter/map), `only`/`exclude` preset arrays, `throttle` ms. Result: `{source: provider.results, destination: provider.results, engine: progress.data}`.

### Decisive source
```ts
// transfer() — fixed lifecycle; rollback + rethrow on ANY failure
this.#emitTransferUpdate('init');
await this.bootstrap();
await this.init();
await this.integrityCheck();
this.#emitTransferUpdate('start');
await this.beforeTransfer();
await this.transferSchemas();
await this.transferEntities();
await this.transferAssets();
await this.transferLinks();
await this.transferConfiguration();
await this.close();
this.#emitTransferUpdate('finish');
```
```ts
// #transferStage — one pipeline() per stage with a fresh AbortController stored for cancellation
const controller = new AbortController();
this.#currentStreamController = controller;
await pipeline(streams, { signal });   // [source, transform?, tracker?, destination]
```
```ts
// shouldSkipStage — schemas can never be skipped; exclude subtracts from an included set
if (stage === 'schemas') { return false; }
let included = isEmpty(only);
...
if (exclude && exclude.length > 0) {
  if (included) {
    included = !exclude.some((transferGroup) => TransferGroupPresets[transferGroup][stage]);
  }
}
```
```ts
// skipped/absent streams are still closed cleanly, then a skip event is emitted
const results = await Promise.allSettled(
  [source, destination].map((stream) => {
    if (!stream || stream.destroyed) { return Promise.resolve(); }
    return new Promise((resolve, reject) => {
      stream.on('close', resolve).on('error', reject).destroy();
    });
  })
);
...
this.#emitStageUpdate('skip', stage);
```

**Flow:** constructor validates both providers (`validateProvider` rejects wrong `type`) → `transfer()` resets `progress.data` → bootstrap both providers via `Promise.allSettled` and `panic()` on any rejection → `init()` resolves both metadata objects and pushes source metadata into the destination via `setMetadata('source', ...)` → `integrityCheck()` (version + schema strategies) → `beforeTransfer()` on source then destination (each error first offered to registered error handlers via `attemptResolveError`) → five stages in the fixed order schemas → entities → assets → links → configuration, each = `pipeline([source, transform?, tracker?, destination], {signal})` → `close()` both providers → emit finish. Any throw: emit `transfer::error`, report the diagnostic only if it differs from the last reported error object, `await destinationProvider.rollback?.(e)`, rethrow.
**Invariant:** stage order is fixed and schemas always runs (it is the integrity baseline); a stage whose source or destination stream is missing is SKIPPED, not failed — but its half-open streams must still be destroyed before the skip event; cancellation goes through the stored AbortController so the in-flight `pipeline` aborts rather than leaking; rollback belongs to the DESTINATION only (the source was never mutated); the diagnostic dedupe compares the error object identity against the last stack item so a panic inside a handler does not double-report.
**Probe:** `packages/core/data-transfer/src/engine/__tests__/engine.test.ts` — 'calls all provider stages' (469–477) pins every provider stage called exactly once; the `exclude`/`only` preset matrix (480–640) pins which `create*WriteStream` is NOT called per preset combination; 'emits stage::skip events' (778–797) pins 3 skips when 3 source stages are deleted; 'all stage streams are destroyed after successful transfer' (1626+) pins no leaked streams.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "transferStage pipeline shouldSkipStage rollback", file_pattern: "packages/core/data-transfer/src/engine/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 4 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the shape: providers own stream creation, the engine owns ordering/cancellation/rollback; the allSettled+panic bootstrap pattern (one bad provider kills the transfer, but you see WHICH one); the "skip ≠ fail" rule for absent streams with mandatory destroy-before-skip; and destination-only rollback. Adapt the stage list, preset names, and the `setMetadata('source', ...)` handshake to your data kinds. Omit Strapi's entity/link schema-filtering transforms (they depend on its content-type schema shape) and the diagnostic reporter's concrete event shape. Coverage caveat: the engine test suite is the direct behavioral pin; no integration test exercises a real remote pair here.
