<!-- capsule-v2 -->
# Solid resource FSM — how does createResource dedupe racing fetches and keep the previous value during refresh?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** How are out-of-order promise resolutions handled, and what is the exact state machine of a resource?

## createResource: pr-identity guard + five-state ladder
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:createResource` (:598-769), core guards `loadEnd` (:649-666) and `load` (:696-743).
**Signature:** `createResource(source?, fetcher, options?) → [read: Resource<T>, { refetch, mutate }]` — 2-vs-3 arg overload resolved by `typeof pFetcher === "function"`.
**Data Shape:** state signal `"unresolved" | "pending" | "ready" | "refreshing" | "errored"`; `pr` = in-flight promise identity; `latest` getter reads `value()` WITHOUT throwing on pending (only errors rethrow); `refetching` info passes `refetch(info)`'s argument into the fetcher.

### Decisive source
```ts
function loadEnd(p: Promise<T> | null, v: T | undefined, error?: any, key?: S) {
    if (pr === p) {                    // stale-response guard: only the CURRENT fetch commits
      pr = null;
      key !== undefined && (resolved = true);
      if ((p === initP || v === initP) && options.onHydrated)
        queueMicrotask(() => options.onHydrated!(key, { value: v }));
      initP = NO_INIT;
      if (Transition && p && loadedUnderTransition) {
        Transition.promises.delete(p);
        loadedUnderTransition = false;
        runUpdates(() => { Transition!.running = true; completeLoad(v, error); }, false);
      } else completeLoad(v, error);
    }
    return v;
}
```

**Flow:** source change → memo-wrapped `load(false)` → null/false source short-circuits to "unresolved" keeping last value → fetcher runs UNTRACKED inside try/catch (sync throw becomes errored state) → non-promise results commit synchronously via loadEnd → promises set `pr`, mark scheduled (one `queueMicrotask` debounce so multiple synchronous triggers coalesce), flip state to pending/refreshing, and register `.then/.catch` handlers bound with the SAME `p` → resolution commits only if `pr === p`.
**Invariant:** Out-of-order test ("test out of order", resource.spec :52-63): trigger("2") then trigger("3"); resolving 3 before 2 still yields "Jake" — because the second load overwrote `pr`, so request-1's `loadEnd(pr_old, ...)` fails the identity check. During refresh (`resolved === true`) the OLD value stays readable while `state === "refreshing"`; error state only throws on read when no fetch is in flight (`if (err !== undefined && !pr) throw err`, :681).
**Probe:** `grep -c 'if (pr === p) {' packages/solid/src/reactive/signal.ts` → `1`; `grep -c 'loadedUnderTransition' packages/solid/src/reactive/signal.ts` → `5`. Behavior pinned by the whole `test/resource.spec.ts` suite (442 lines, 8 describes).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "createResource loadEnd completeLoad refetching", limit: 10 });
```

## Verdict
Adopt the promise-identity guard + keep-last-value refresh semantics + NO_INIT sentinel for "no initialValue". Adapt storage injection (`options.storage`) to host state layers. Omit SSR `sharedConfig.load/getNextContextId` plumbing until hydration is ported.
