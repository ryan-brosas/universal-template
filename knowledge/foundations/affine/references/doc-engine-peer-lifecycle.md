<!-- capsule-v2 -->
# DocEngine main/shadow choreography — ordered startup and graceful-stop gate

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** Why does the engine start shadow peers only after the main peer loads, and how do callers stop without losing local writes?

## DocEngine.sync + canGracefulStop
**Path/Symbol:** `blocksuite/framework/sync/src/doc/engine.ts`: `DocEngine.sync()` (:116-196), `canGracefulStop()` (:85-87), `waitForGracefulStop()` (:217-237).
**Signature:** `async sync(signal: AbortSignal)` (never returns until abort); `canGracefulStop(): boolean`.
**Data Shape:** `DocEngineStatus { step, main: DocPeerStatus|null, shadows: (DocPeerStatus|null)[], retrying }`; engine owns one `SharedPriorityTarget` shared with every peer queue.

### Decisive source
```ts
// Step 1-4 ordering is the contract
state.mainPeer = new SyncPeer(this.rootDoc, this.main, this.priorityTarget, this.logger);
await state.mainPeer.waitForLoaded(signal);          // Step 2 BEFORE shadows
state.shadowPeers = this.shadows.map(shadow => new SyncPeer(this.rootDoc, shadow, ...));
await new Promise((_, reject) => signal.addEventListener('abort', () => reject(signal.reason)));
// finally: every peer .stop(); every subscriber unsubscribed
```
```ts
canGracefulStop() {
  return !!this.status.main && this.status.main.pendingPushUpdates === 0;
}
```

**Flow:** `start()` force-stops any previous run, makes a fresh AbortController, calls `sync()` → main peer constructed → wait for its status ≥ LoadingSubDoc → shadow peers constructed together → park on abort → finally stops all peers and cleans subscriptions. Status aggregation (`updateSyncingState`) walks `[main, ...shadows]`: ANY peer not Synced ⇒ engine Syncing; any Retrying ⇒ retrying flag.

**Invariant:** Shadows never start before the main peer has pulled root content — otherwise each shadow pull races the initial local push and duplicates work. Graceful stop waits for `pendingPushUpdates === 0` on MAIN ONLY (shadow loss is acceptable; main loss loses data); `forceStop()` bypasses this deliberately. The engine's `waitForSynced` resolves only when ALL peers report `Synced`, so a permanently broken shadow keeps the doc "syncing" forever — porters must decide whether that is desired.

**Probe:** `blocksuite/framework/store/src/test/test-workspace.ts` :97-107 constructs `DocEngine(rootDoc, docSources.main, docSources.shadows ?? [])` as the canonical wiring (`grep -n "new DocEngine" blocksuite/framework/store/src/test/test-workspace.ts`). No dedicated engine unit spec — lifecycle pinned by construction site + source order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "DocEngine sync waitForLoaded canGracefulStop", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt main-before-shadow ordering and push-drained graceful stop; adapt status aggregation to host UI needs; omit the rxjs Subject layer if a host already has an event bus.
