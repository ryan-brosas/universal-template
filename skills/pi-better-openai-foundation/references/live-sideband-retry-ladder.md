<!-- capsule-v2 -->
# Sideband connect retry ladder — how do you retry a flaky WebSocket handshake without hammering or leaking?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** What is the bounded retry/backoff/timeouts contract for opening the live sideband WebSocket?

## Retry ladder
**Path/Symbol:** `src/live/transport.ts:#connectSideband` (:231-250) over `#openSideband` (:252-340); constants `SIDEBAND_CONNECT_ATTEMPTS=5`, `SIDEBAND_CONNECT_TIMEOUT_MS=15_000` (:19-20).
**Signature:** `#openSideband(callId, credentials, attestation): Promise<void>` — resolves exactly once on `open`, rejects otherwise.

### Decisive source
```ts
for (let attempt = 0; attempt < SIDEBAND_CONNECT_ATTEMPTS; attempt += 1) {
  try { await this.#openSideband(...); return; }
  catch (cause) {
    failure = errorFrom(cause);
    if (this.#operationSignal.aborted) throw abortReason(this.#operationSignal);
    if (attempt + 1 < SIDEBAND_CONNECT_ATTEMPTS)
      await wait(200 * 2 ** attempt, this.#operationSignal);
  }
}
throw failure;
```
Inside `#openSideband`: a `settled` latch makes resolve/reject idempotent (:268-299); abort closes the socket `1000 "aborted"` before rejecting; late `open` after settle closes the orphan socket `"stale"` (:289-299); pre-open `error` rejects + terminates, post-open `error` reports failure instead (:307-315); post-open `close` reports failure ONLY if this socket is still the current `#sideband` (:316-327); the whole wait honors the shared `#operationSignal` and the timer is `unref()`ed.

**Flow:** attempt → settle-once outcome → abort check beats retry → exponential 200/400/800/1600ms waits (abortable) → last failure thrown verbatim.
**Invariant:** Abort ALWAYS outranks retry (checked before scheduling each backoff); the LAST cause is preserved as `failure` and rethrown — never swallowed into a generic error; no retry after the operation signal aborted.
**Probe:** `tests/live-transport.test.ts` (URL/header builders pin the constants' consumers; the ladder itself is exercised via controller integration in `tests/live-controller.test.ts` — direct ladder-timing test absent at this pin, caveat recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "SIDEBAND_CONNECT_ATTEMPTS openSideband", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the settled-latch single-shot promise wrapper + attempts×exponential-abortable-wait shape. Adapt attempt counts/base delay/timeout to your SLA. Omit Codex header assembly (auth capsule covers credentials).
