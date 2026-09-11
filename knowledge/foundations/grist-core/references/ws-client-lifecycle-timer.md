<!-- capsule-v2 -->
# ws-client-lifecycle-timer — How long does a disconnected Client linger, and what is the exact destroy choreography?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** When the socket drops, when is server-side client state reclaimed, and in what order does destruction proceed?

## Destroy timer + reclamation order
**Path/Symbol:** `clientRemovalTimeoutMs = 300_000` (:31), DI hook `Deps = {clientRemovalTimeoutMs, jsonResponseReservation}` :42; timer armed `_onClose` :591–606, cleared `sendConnectMessage` :338–341; `destroy()` :456–466; `destroyAllClients` Comm :140–147.
**Signature:** `_destroyTimer = setTimeout(() => this.destroy(), Deps.clientRemovalTimeoutMs)`; destroy: closeAllDocs → clear timer → _dropMissedMessages(_nextSeqId) → comm.removeClient → _destroyed=true.
**Data Shape:** 5-minute grace; Deps object exists so tests can shorten it (DI seam).

### Decisive source
```ts
public destroy() {
  const docsClosed = this.closeAllDocs();
  this._log.info({ docsClosed }, "client gone");
  if (this._destroyTimer) { clearTimeout(this._destroyTimer); this._destroyTimer = null; }
  this._dropMissedMessages(this._nextSeqId);
  this._comm.removeClient(this);
  this._destroyed = true;
}
```

**Flow:** socket close ⇒ strip listeners, null websocket ref, if not already destroyed: cancel any prior pending timer ("clearing previously scheduled destruction") then arm fresh 5-min timer → SAME client reconnects within grace ⇒ sendConnectMessage clears timer FIRST thing ⇒ timer fires ⇒ destroy(): close all doc sessions (counting, error-swallowed per-doc) → drop ENTIRE ledger → deregister from Comm map → latch _destroyed → sendMessage on destroyed client becomes silent no-op (:244–246).
**Invariant:** the grace window IS the seamless-reconnect budget — reconnect after expiry gets a new Client and a reload. Re-arm-not-stack: a second disconnect replaces rather than doubles timers. destroyAllClients snapshots the map FIRST (`Array.from`) because iteration mutates during removal. _destroyed makes sends vanish silently rather than throw — late async responses from methods still running must not error.
**Probe:** `test/server/Comm.ts` uses waitForSocketRelease helper throughout (e.g. :619–663) pinning release-after-close timing via the DI'd timeout.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "closeAllDocs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt grace-timer + re-arm-not-stack + ordered destroy + silent-after-destroy sends. Adapt the 300s window to product needs; keep the Deps-style DI seam for tests. Omit docFD specifics if you have no per-doc session registry.
