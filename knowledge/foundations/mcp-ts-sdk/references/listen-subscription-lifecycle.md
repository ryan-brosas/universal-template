<!-- capsule-v2 -->
# subscriptions/listen caller lifecycle — how does a client hold a long-lived server push stream with one idempotent settle and a transport-agnostic teardown?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** How does `Client.listen()` guarantee exactly-once termination across ack/timeout/cancel/abort/stream-end/transport-close, and how does teardown reach both HTTP and stdio transports?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/client.ts`: `listen` (:1949-2125), `_onclose` override (:2265-2274), `_resetConnectionState` listen-settle branch (:588-602), string-id contract comment (:561-569); direct test `packages/client/test/client/listen.test.ts`.
**Signature:** `async listen(filter: SubscriptionFilter, options?: RequestOptions): Promise<McpSubscription>` where `McpSubscription = { honoredFilter; close(): Promise<void>; closed: Promise<'local'|'graceful'|'remote'> }`
**Data Shape:** `_listenState: Map<'listen:N', { settle }>`; wire request `{id:'listen:N', method:'subscriptions/listen', params:{_meta:<envelope>, notifications:filter}}`.

### Decisive source
```ts
// :2011-2043 — every termination funnels through one guarded settle
const settle = (outcome) => {
    if (state === 'closed') return;                       // idempotent by construction
    …clear ackTimer…;
    if ('ack' in outcome) { state = 'open'; resolveOpening(outcome.ack); return; }
    state = 'closed';
    options?.signal?.removeEventListener('abort', onCallerAbort);
    this._listenState.delete(listenId);
    requestAbort.abort();                                 // closes HTTP SSE reader post-ack too
    resolveClosed(outcome.cause);
    if (wasOpening) rejectOpening(outcome.error ?? new SdkError(ConnectionClosed, 'closed before the server acknowledged'));
};
// :2055-2058 — dual-channel teardown, transport-agnostic
const wireTeardown = async () => {
    requestAbort.abort();                                  // HTTP honors requestSignal
    await this.notification({ method: 'notifications/cancelled', params: { requestId: listenId } }).catch(() => {}); // stdio router honors this
};
```

**Flow:** NotConnected guard FIRST (post-close the cleared era would make the era guard lie) →
modern-era-only else typed `MethodNotSupportedByProtocolVersion` steering to listChanged +
resources/subscribe → already-aborted signal rejects pre-setup with request()'s exact
`SdkError(RequestTimeout)` wrap → register state BEFORE send (synchronous ack cannot race) → ack
timer settles remote+RequestTimeout → send carries `requestSignal` + `onRequestStreamEnd`
(stream end ⇒ settle remote). Remote close reaches machines via the `_onclose` override BEFORE
super tears down (listen ids are never in `_responseHandlers`, so base settlement can't reach them).

**Invariant:** the subscription id is a STRING from a Client-owned `'listen:'+N` counter — JSON-RPC
legal, demuxable from Protocol's numeric ids by string-ness alone, echoed verbatim as
`notifications/cancelled.requestId`. Termination causes are trichotomous: `'local'` (user
close/signal), `'graceful'` (server's SubscriptionsListenResult), `'remote'` (cancel/stream-end/
transport drop); late arrivals after closed are no-ops or pass to the fallback notification handler,
never swallowed. `close()` clears per-connection state even when the transport's close REJECTS.

**Probe:** `packages/client/test/client/listen.test.ts` :382-406 (pre-aborted ⇒ RequestTimeout wrap,
no wire write), :408-469 (abort while opening rejects fast + cancelled echoes the id; abort while
open ⇒ 'local' + single cancelled + idempotent re-close), :863-884 (string id on the wire +
verbatim cancel echo + envelope present), :886-911 (`onRequestStreamEnd` ⇒ 'remote', no leaked
state), :913-923 (state reset even on rejecting transport.close()).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", query: "subscriptions listen settle wireTeardown McpSubscription", limit: 10 });
```

## Verdict
Adopt the settle-funnel + dual-channel teardown for any long-lived push subscription over mixed
transports; adapt cause vocabulary to your domain; omit the graceful-result leg if your server has
no explicit close frame. Complements: sse-resume-reconnection-kernel.md (transport-side intentional-
abort gate this signal feeds), listen-router.md (server side: ack-first frames, capacity),
input-required-driver.md (the other modern-era client driver).
