<!-- capsule-v2 -->
# Protocol correlation kernel — how do per-request handler maps, era gates, and the dual-timeout loop correlate responses on one connection?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the correlation kernel every MCP peer runs — registration, era validation, progress resets, and cancellation hand-off?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/protocol.ts`: abstract class `Protocol` (:558) owning the `_responseHandlers` / `_progressHandlers` / `_timeoutInfo` maps and `_pendingDebouncedNotifications` (:566-567); request funnel `_onrequest` (:929-1162) with wire-lift (:933), unclassified-drop consult (:947-951), era-mismatch gate (:969-976), response-handler registration (:1493); progress path `_onprogress` (:1164-1191, conditional `_resetTimeout` :1177-1179); timeouts `_setupTimeout` (:737-752), `_resetTimeout` (:754-770), `_cleanupTimeout` (:772-778).
**Signature:** `abstract class Protocol<ContextT extends BaseContext>`; `protected _onrequest(rawRequest: JSONRPCRequest, extra?: MessageExtraInfo): void`; `classifiedWireEra(classification: MessageClassification): WireEra` (`wire/codec.ts` :315-318).
**Data Shape:** per-request timeout record `{ timeoutId, timeout, maxTotalTimeout?, startTime, resetTimeoutOnProgress }` keyed by message id alongside the response handler under the SAME key; `MessageExtraInfo.classification` optional (hand-wired legacy transports never classify).

### Decisive source
```ts
// protocol.ts :969-976 — a classified message naming ANOTHER era is a routing
// error answered loudly; it is never served on a guessed era.
if (extra?.classification !== undefined) {
    const classified = classifiedWireEra(extra.classification);
    if (classified !== codec.era) {
        this._onerror(
            new Error(
                `Era mismatch on inbound request '${request.method}': classified as ${classified} but this instance serves ${codec.era}`
            )
        );
```

**Flow:** inbound request → optional drop consult when unclassified (`_shouldDropInbound` returns 'drop' ⇒ onerror + return) → `liftWireOnlyMaterial` strips envelope/retry fields so handlers (fallback handler and per-method schema parse included) see exactly the 2025-era shape while envelope/retry surface via ctx → resolve outbound codec → classified traffic validated against the INSTANCE era (mismatch = typed onerror, never dispatch) → handler registered keyed by messageId with timeout armed (`DEFAULT_REQUEST_TIMEOUT_MSEC`, optional `maxTotalTimeout`, opt-in `resetTimeoutOnProgress`). Progress resets fire only when the response handler still exists AND the request opted in; `_cleanupTimeout` deletes timer and maps together. Cancellation hand-off (absence-exact id semantics, initialize wire-silence) has its own capsule: cancel-wire-contract.md.

**ERRATUM (pass 5 drift re-entry):** this capsule previously cited a `classifyInboundMessage(body, headers)` symbol with a hand-written excerpt — NEITHER exists at the old pin `cc4b4161` nor at `3924de9`. The real era router is `classifyInboundRequest` (inboundClassification.ts, see inbound-ladder.md); per-message era enforcement happens in THIS class via `classifiedWireEra`. The coalescing claim formerly asserted here is owned by notification-coalescing.md.

**Invariant:** A per-request classification can never SWITCH a live connection's negotiated era — misrouted traffic is answered out-of-band and dropped. Response handlers, progress handlers, and timeout records share the message-id key and are cleaned together; a progress reset requires BOTH a live response handler and `resetTimeoutOnProgress`.

**Probe:** `grep -c "should abort request handler when notifications/cancelled carries requestId" packages/core-internal/test/shared/protocol.test.ts` → 1 (id matrix includes 0 and ''); `grep -c "Era mismatch on inbound request" packages/core-internal/src/shared/protocol.ts` → 1.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "classifiedWireEra _onrequest Protocol", limit: 5 });
```

**Verdict:** Adopt instance-era validation + shared-key cleanup discipline; adapt timeout defaults to your host RPC loop; omit the drop hook if your transport guarantees classification upstream.
