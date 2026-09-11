<!-- capsule-v2 -->
# Debounced notification coalescing — how do repeated list-changed notifications collapse into one send without losing parameters?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the safe rule for coalescing a notification storm (e.g. `tools/list_changed` per mutation) on a live connection?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/protocol.ts`: `_notificationViaCodec` debounce region (:1600-1662, gate :1629-1630), `_pendingDebouncedNotifications` Set (:567), `ProtocolOptions.debouncedNotificationMethods` (:85-90).
**Signature:** internal gate: `canDebounce = debouncedMethods.includes(method) && !notification.params && options?.relatedRequestId === undefined` — the related-request test is STRICT absence (`=== undefined`), not truthiness: ids `0` and `''` are legal, and treating them as absent would let a RELATED notification be coalesced away since the pending set is keyed by method alone.
**Data Shape:** Opt-in per method-name list; only SIMPLE notifications qualify (no params, no related request). Pending marker is a Set of method names — one in-flight slot per method.

### Decisive source
```ts
if (canDebounce) {
    // If a notification of this type is already scheduled, do nothing.
    if (this._pendingDebouncedNotifications.has(notification.method)) return;
    this._pendingDebouncedNotifications.add(notification.method);
    // Schedule the actual send to happen in the next microtask.
    // This allows all synchronous calls in the current event loop tick
    // to be coalesced.
    Promise.resolve().then(() => {
        this._pendingDebouncedNotifications.delete(notification.method);
        if (!this._transport) return;   // SAFETY CHECK: closed while pending → abort
        this._transport?.send(jsonrpcNotification, options).catch(error => this._onerror(error));
    });
    return;
}
```

**Flow:** N synchronous notification() calls within one event-loop tick → first schedules a microtask send and marks pending → rest return immediately (dropped) → microtask fires: unmark FIRST (so a notification arriving during the send can schedule the next tick), then send with `.catch(onerror)`.

**Invariant:** Only parameterless, unrelated notifications may be debounced — params or a related-request id could be lost by collapsing. The unmark-before-send ordering is what keeps the coalescer live under sustained storms while never sending two in one tick.

**Probe:** covered indirectly by protocol-level notification tests; the existing leaf's coalescing claim ("notifications/tools/list_changed … coalesced into a single emit" in references/protocol.md) traces to THIS region (:1611-1648) — recorded as a provenance erratum for that capsule's uncited line range.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "debouncedNotificationMethods _pendingDebouncedNotifications", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt opt-in simple-notification microtask coalescing; adapt the method list to your change events; omit the safety-check branch if sends cannot outlive close in your host.
