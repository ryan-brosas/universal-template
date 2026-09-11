<!-- capsule-v2 -->
# Query.fetch dedup / silent-cancel / revert ladder — when does a concurrent fetch reuse the in-flight promise vs silently cancel vs revert?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** When a second fetch arrives while one is in flight, what exactly happens under each combination of cancelRefetch, silent, revert, and settled-retryer states?

## The fetch entry ladder
**Path/Symbol:** `packages/query-core/src/query.ts:Query.fetch` (lines 401–631).
**Signature:** `async fetch(options?, fetchOptions?): Promise<TData>` where FetchOptions = `{ cancelRefetch?, meta?, initialPromise? }`.
**Data Shape:** instance fields involved: `#retryer?: Retryer`, `#revertState?: QueryState`, `#abortSignalConsumed: boolean`, `state.fetchStatus`.

### Decisive source
```ts
if (
  this.state.fetchStatus !== 'idle' &&
  // If the promise in the retryer is already rejected, we have to definitely
  // re-start the fetch; ...
  this.#retryer?.status() !== 'rejected'
) {
  if (this.state.data !== undefined && fetchOptions?.cancelRefetch) {
    // Silently cancel current fetch if the user wants to cancel refetch
    this.cancel({ silent: true })
  } else if (this.#retryer) {
    // make sure that retries that were potentially cancelled due to unmounts can continue
    this.#retryer.continueRetry()
    return this.#retryer.promise
  }
}
```
and the cancellation consumption contract:
```ts
const addSignalProperty = (object: unknown) => {
  Object.defineProperty(object, 'signal', {
    enumerable: true,
    get: () => {
      this.#abortSignalConsumed = true
      return abortController.signal
    },
  })
}
```
plus removeObserver:
```ts
if (this.#abortSignalConsumed || this.#isInitialPausedFetch()) {
  this.#retryer.cancel({ revert: true })
} else {
  this.#retryer.cancelRetry()
}
```

**Flow:** second fetch while non-idle AND retryer not rejected → (a) has data + cancelRefetch ⇒ silent-cancel current, fall through to start a NEW fetch (its catch sees `error.silent` and piggybacks on `this.#retryer.promise` — the NEW retryer's promise); (b) otherwise ⇒ continueRetry (un-latch any unmount cancellation) and RETURN the existing promise — no new request. On unmount (removeObserver to zero observers): if the queryFn actually READ context.signal (`#abortSignalConsumed` latched by the getter) or the fetch never started (`paused`+`pending`), cancel({revert:true}) restores `#revertState` with fetchStatus 'idle'; otherwise only future RETRIES are cancelled — the in-flight result is still cached. In the success catch: `silent` ⇒ return new retryer promise; `revert` ⇒ return current data or rethrow CancelledError if none; plain error ⇒ dispatch error action. finally: `if (this.#retryer === retryer) this.#retryer = undefined` (drop OUR retryer only — identity guard against a newer fetch having replaced it) then scheduleGc().
**Invariant:** (1) a rejected-but-not-yet-restarted retryer NEVER dedupes — the ladder falls through to a fresh fetch; (2) signal consumption is detected lazily via a property getter, NOT by wrapping the queryFn — porters who pass a plain signal object lose the abort-on-unmount-with-consumption behavior; (3) the finally-block identity check prevents an older fetch's cleanup from dropping a NEWER fetch's retryer.
**Probe:** `grep -c "abortSignalConsumed" packages/query-core/src/query.ts` (=6: field decl :174, reset :179, unmount branch :371, comment :448, latch :454, per-fetch reset :480) and `grep -n "data is undefined" packages/query-core/src/query.ts` (:576 — undefined-data runtime guard after successful await).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^fetch$|fetchState", limit: 5, fields: ["name", "file", "lines"] });
```

## Verdict
Adopt the full ladder including the lazy signal-consumption probe and the finally identity-guard — both prevent classic port bugs (stuck fetching states, dropped newer fetches). Adapt CancelledError routing to your error taxonomy but keep the three-way silent/revert/plain distinction. Omit persister indirection inside fetchFn unless you have a persistence layer. Direct tests: `__tests__/query.test.tsx` (cancelled/paused matrix) cited, not executed this window.
