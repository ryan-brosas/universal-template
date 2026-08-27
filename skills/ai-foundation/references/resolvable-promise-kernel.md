<!-- capsule-v2 -->
# Resolvable promise + hanging-stream warning — what kernel do both RSC streamables share?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How is "externally resolvable promise" implemented, and how do streamable objects warn about forgotten `.done()`?

## createResolvablePromise
**Path/Symbol:** `packages/rsc/src/util/create-resolvable-promise.ts` (:10-28); warning timer shared by `create-streamable-value.ts:warnUnclosedStream` (:146-159) and `create-streamable-ui.tsx` (:66-79); constant `packages/rsc/src/util/constants.ts`.
**Signature:** `createResolvablePromise<T>(): {promise, resolve(value), reject(error)}` — the classic executor-captured pair.
**Data Shape:** none — 28-line kernel; the PATTERN is the capsule.

### Decisive source
```ts
const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
return { promise, resolve: resolve!, reject: reject! };
// dev-only watchdog re-armed on EVERY update, cleared on error/done:
warningTimeout = setTimeout(() => {
  console.warn('The streamable value has been slow to update. This may be a bug or a performance issue or you forgot to call `.done()`.');
}, HANGING_STREAM_WARNING_TIME_MS);
```

**Flow:** create → arm dev timer (guarded by `process.env.NODE_ENV === 'development'`) → each update/append clears + re-arms → error/done clear permanently. Both RSC streamables and the suspended-chunk driver build on this single kernel.
**Invariant:** production never pays the timer cost; the warning text names the actual failure mode (missing `.done()` leaves clients pending forever — see streamable-value-protocol).
**Probe:** covered transitively by `create-streamable-value.test.tsx` / `create-streamable-ui.ui.test.tsx`; no direct unit test for the kernel itself (coverage caveat: trivial 28L util, behavior exercised via its two consumers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createResolvablePromise HANGING_STREAM_WARNING_TIME_MS", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as-is. Pair with streamable-value-protocol + streamable-ui-suspense-ladder capsules.
