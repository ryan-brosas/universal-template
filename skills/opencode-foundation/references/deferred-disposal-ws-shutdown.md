<!-- capsule-v2 -->
# Deferred disposal & graceful socket shutdown — how do you tear down per-request resources after the response is sent, and close every WebSocket deterministically at server exit?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How can a handler request work that must happen AFTER the HTTP response is produced, and how should a server close tracked sockets on shutdown?

## Request-keyed WeakMap handoff + closing latch
**Path/Symbol:** `packages/opencode/src/server/routes/instance/httpapi/lifecycle.ts` (`disposeAfterResponse` :16, `markInstanceForDisposal` :23-33, `markInstanceForReload` :35-41, `disposeMiddleware` :43-54) + `.../websocket-tracker.ts` (`Interface` :9-13, `layer` :17-46, `register` :50-58).
**Signature:** `markInstanceForDisposal(ctx) → Effect<void>` (handler-side); `disposeMiddleware: HttpMiddleware` (outer); `register(close: Effect<void>) → Effect<boolean>`; `closeAll → Effect<void>`.
**Data Shape:** `WeakMap<object /* original Request */, MarkedInstance{ctx, store, bridge}>`; tracker holds `Set<Close>` plus a `closing` boolean.

### Decisive source
```ts
// lifecycle.ts:13-15 — the pattern rationale, verbatim:
// Disposal is requested by an endpoint handler, but must run from the outer
// server middleware after the response has been produced. The original Request
// object is the stable handoff key between those two phases.
const disposeAfterResponse = new WeakMap<object, MarkedInstance>()
// websocket-tracker.ts:21-26 — late connections are rejected once shutting down:
add: (close) => Effect.gen(function* () {
  if (closing) return false
  sockets.add(close)
  return true
}),
```

**Flow (disposal):** handler effect calls `markInstanceForDisposal(ctx)` ⇒ pre-response handler stashes marked instance keyed by `request.source` ⇒ response returns normally ⇒ OUTER `disposeMiddleware` (wired into `HttpRouter.toWebHandler(..., {middleware: disposeMiddleware})`) reads+deletes the WeakMap entry and runs `store.dispose(ctx)` **uninterruptibly**, logging failures as warnings (`Effect.catchCause → logWarning`). Reload variant differs: `markInstanceForReload` awaits the reload BEFORE the response via `Effect.as(Effect.uninterruptible(bridge.run(store.reload(next))), response)`.
**Flow (shutdown):** `closeAll` sets `closing=true`, snapshots the set, clears it, then closes every registered close-effect with `Effect.timeout("1 second")` under unbounded concurrency, swallowing all errors. `register` is service-optional (absent tracker ⇒ proceed) and idempotent-failing after the latch (`add→false` ⇒ caller knows it was rejected).
**Invariant:** Disposal never delays or fails the response; reload DOES delay the response but cannot be interrupted. The WeakMap key must be the ORIGINAL Request object (stable identity across middleware phases). Shutdown closes each socket with its own timeout — one hung socket cannot stall the rest.
**Probe:** source pins (no dedicated upstream test file for these two units — coverage caveat recorded):
```bash
grep -n "disposeAfterResponse = new WeakMap" packages/opencode/src/server/routes/instance/httpapi/lifecycle.ts
grep -n "closing = true" packages/opencode/src/server/routes/instance/httpapi/websocket-tracker.ts
```
expect 1 hit each (:16, :32).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "websocket tracker closeAll server closing graceful dispose after response", limit: 8 });
```

## Verdict
Adopt WeakMap-request-keyed post-response handoff for teardown work and the latch+per-socket-timeout shutdown registry; adapt what "dispose/reload" means on your host; note the missing direct-test caveat when reusing.
