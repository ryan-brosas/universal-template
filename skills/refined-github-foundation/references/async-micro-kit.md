<!-- capsule-v2 -->
# Async Utility Micro-Kit — what are the minimal correct shapes for onetime, abortable delay, waitFor polling, and parallel async iteration?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** Which tiny async primitives does the codebase rely on, and what invariants do porters get wrong?

## Connected graph-selected seam
Four helpers with fan-in across the whole tree (onetime 20, delay 12, waitFor inside feature-manager's boot).

**Path/Symbol:** `source/helpers/onetime.ts` (:1–14); `source/helpers/delay.ts` (:1–10); `source/helpers/wait-for.ts` (:3–8); `source/helpers/async-for-each.ts` (:2–7); `source/helpers/map-of-arrays.ts:ArrayMap`.
**Signature:** `onetime<A,R>(fn): (...a:A)=>R`; `delay(ms: number, signal?: AbortSignal): Promise<void>`; `waitFor(condition: () => any): Promise<void>`; `asyncForEach<Item>(iterable, iteratee): Promise<void>`.
**Data Shape:** `ArrayMap<K,V> extends Map<K,V[]>` adds only `append(key, ...values)` (create-if-missing then push) — the registry type behind per-feature controller lists.

### Decisive source
```ts
// onetime — sentinel instead of undefined so a fn returning undefined still runs once
const notRun = Symbol('false');
let returnValue = notRun;
return function (this, ...args) {
	if (returnValue !== notRun) return returnValue;
	returnValue = Reflect.apply(fn, this, args);
	return returnValue;
};
```
```ts
// delay — reject with the SIGNAL'S OWN reason, never a synthetic Error
signal?.addEventListener('abort', () => {
	clearTimeout(timeout);
	reject(signal.reason);
});
// waitFor — poll loop; condition may be sync truthiness
while (!condition()) await delay(10);
// asyncForEach — parallel map over a COPY of the iterable
await Promise.all([...iterable].map(async item => iteratee(item)));
```

**Flow:** onetime caches by sentinel (not falsy-check); delay converts an abort into a rejection carrying `signal.reason` (so `throwIfAborted` semantics propagate upstream); waitFor is a fixed-10ms poll used only at boot (`waitFor(() => document.body)`); asyncForEach fans out concurrently and never serializes.
**Invariant:** do NOT replace the onetime sentinel with `if (cached)` — functions returning `undefined` would re-run forever. Do NOT swallow/reject-with-new-Error in delay — callers match on `signal.reason`. `asyncForEach` copies the iterable first because generators/NodeLists mutate during iteration.
**Probe:** no dedicated unit tests for these three (trivial size); behavior is pinned by usage: `feature-manager.tsx:99` (`waitFor(() => document.body)`), :185 + :226 (`void asyncForEach(...)` fire-and-forget), selector-observer.tsx:25 (`onetime(registerAnimation)`). Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "onetime delay waitFor asyncForEach ArrayMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all four + ArrayMap as the standard async micro-kit for browser extensions. Adapt timing constants (10ms poll). Omit nothing. Caveat: direct tests absent by design; invariants above are source-cited.
