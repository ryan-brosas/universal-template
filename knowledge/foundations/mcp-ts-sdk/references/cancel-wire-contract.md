<!-- capsule-v2 -->
# Cancel wire contract — which cancellations reach the wire, and why request id `0` must never be treated as absent?

**Source:** typescript-sdk MIT `main@3924de9` (commits 03842cd9 #2654 + 3e90449f #2668); Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When an in-flight request is aborted or times out, what exactly goes on the wire — and where do porters get request ids wrong?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/protocol.ts`: `_oncancel` (:726-735), the per-request `cancel()` closure inside `_onrequest` (initialize wire-guard :1464-1481), debounce gate in `_notificationViaCodec` (:1629-1630).
**Signature:** `private async _oncancel(notification: CancelledNotification): Promise<void>`, gate `if (notification.params.requestId === undefined) return;`; outbound gate `if (request.method !== 'initialize') { …send notifications/cancelled… }`.
**Data Shape:** `CancelledNotification.params.requestId` is OPTIONAL on the 2025-era wire schema; legal ids include `0` (the first id every zero-based counter assigns) and `''`.

### Decisive source
```ts
// packages/core-internal/src/shared/protocol.ts :726-735
private async _oncancel(notification: CancelledNotification): Promise<void> {
    // `requestId` is optional on the 2025-era wire schema. Absent is the
    // only thing that means "no id": `0` and `''` are legal request ids.
    if (notification.params.requestId === undefined) {
        return;
    }
    // Handle request cancellation …
```

**Flow:** INBOUND notifications/cancelled → `_oncancel`: absent requestId ignored; `0`/`''` look up the pending handler and abort its context signal like any other id. OUTBOUND legacy era: caller abort or timeout reaches the per-request `cancel()` closure → sends `notifications/cancelled {requestId, reason}` — EXCEPT `initialize`, whose cancellation the spec forbids outright ("A client MUST NOT attempt to cancel its initialize request"): the caller promise still rejects locally but NOTHING goes on the wire. Only legacy instances can hit this — `initialize` is absent from the modern registry, which negotiates via `server/discover`. Modern era: aborting the request's underlying stream IS the spec cancel signal; no notification is synthesized.

**Invariant:** `=== undefined` is the ONLY absence test for a wire-optional id — a truthiness guard (`!requestId`) silently swallows `0` and `''`. The same rule governs the debounce gate (`options?.relatedRequestId === undefined`): the pending set is keyed by method alone, so treating id `0` as absent would let a RELATED notification be coalesced away. Initialize cancellation settles purely locally on every transport.

**Probe (direct tests):** `packages/core-internal/test/shared/protocol.test.ts` — id matrix `test.each([0, 123, '', 'req-1'])` appears TWICE: :802 'should abort request handler when notifications/cancelled carries requestId %j' (comment above names `0` as "the first id every peer assigns, since the counter is zero-based") and :664 'should NOT coalesce same-tick notifications related to requestId %j' ("`0` and `''` are the ids a truthiness guard swallows" — the DEBOUNCE side of the same rule); describe 'the initialize handshake is never cancelled on the wire' (:955-990): abort case :956, timeout case :970, plus :987 'every other method still POSTs notifications/cancelled (regression guard)' asserting `cancelledSent(sent)).toHaveLength(1)` (that assertion also appears at :916 under the stdio-MUST-send spec pin).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "_oncancel CancelledNotification", limit: 5 });
// → Protocol._oncancel Method packages/core-internal/src/shared/protocol.ts 726-735
```

**Verdict:** Adopt strict `=== undefined` absence semantics for optional wire ids and silent-local initialize cancellation; adapt reason wrapping (SdkError RequestTimeout) to your error taxonomy; omit the modern AbortSignal leg if your transport has no per-request streams.
