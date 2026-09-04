<!-- capsule-v2 -->
# AbortSignal plumbing — how do user-supplied abort signals cancel an in-flight RPC?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** When a caller passes an AbortSignal, what must happen on the wire, to the pending promise, and to the error cause — before, during, and after the call?

## Three-point integration: preflight, wire message, waiter
**Path/Symbol:** `packages/playwright-core/src/client/connection.ts:sendMessageToServer` (188-223) + `client/waiter.ts:rejectOnTimeout` (83-98) + errors (`client/errors.ts:AbortError` 41-46).
**Signature:** options `{ signal?: AbortSignal }`; wire event `{ guid, method: '__abort__', params: { id, reason } }`; `rejectOnTimeout` treats an already-aborted signal as immediate AbortError.
**Data Shape:** abort reason normalized: `signal.reason instanceof Error ? signal.reason.message : String(signal.reason)`; listener registered with `{ once: true }` and removed in `finally`.

### Decisive source
```ts
const signal = options.signal;
if (signal?.aborted)
  throw new AbortError(undefined, { cause: signal.reason });
...
let abortListener: (() => void) | undefined;
if (signal) {
  abortListener = () => {
    const reason = signal.reason instanceof Error ? signal.reason.message : String(signal.reason);
    emptyZone.run(() => this.onmessage({ guid, method: '__abort__', params: { id, reason } }));
  };
  signal.addEventListener('abort', abortListener, { once: true });
}
try {
  return await new Promise((resolve, reject) => this._callbacks.set(id, { resolve, reject, signal, title: options.title, type, method }));
} finally {
  if (abortListener)
    signal!.removeEventListener('abort', abortListener);
}
```

**Flow:** (1) preflight — already-aborted signals throw synchronously with the raw reason as `cause`; (2) in-flight — an abort fires a synthetic `__abort__` EVENT through the same dispatch pump (not a control channel), carrying the numeric id and stringified reason; the server cancels the operation; (3) settlement — when the server's eventual rejection arrives, dispatch checks `callback.signal?.aborted && parsedError instanceof AbortError` and sets `parsedError.cause = callback.signal.reason`, preserving the USER's reason object rather than the transport's copy; (4) cleanup — the listener is removed in `finally` whether the call resolved, rejected, or the connection closed. Client-side waiters integrate at a second point: `rejectOnTimeout` rejects immediately for pre-aborted signals and registers its own once-listener otherwise.
**Invariant:** The abort listener MUST be removed exactly once (once:true + finally removal); the wire-side reason is a string but the client-visible `cause` is the original reason value; aborting must work even when no response ever arrives (the `__abort__` path does not depend on the reply).
**Probe:** `grep -c "emptyZone.run" packages/playwright-core/src/client/connection.ts` → `2` (send + __abort__ paths); `grep -cn "signal.addEventListener('abort', abortListener, { once: true })" packages/playwright-core/src/client/connection.ts` → `1`; `grep -c "'__abort__'" packages/playwright-core/src/client/connection.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "AbortError sendMessageToServer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt preflight-throw, synthetic-wire-event cancellation keyed by request id, cause preservation from the user's signal, and finally-block listener hygiene. Adapt the `__abort__` mechanism to your protocol's control message. Omit the Error/string reason normalization only if your runtime guarantees Error reasons. No dedicated unit test isolates the signal path at this commit (exercised via API-level signal tests in the library suite); keep grep pins as commit-scoped evidence.
