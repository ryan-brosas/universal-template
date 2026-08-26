<!-- capsule-v2 -->
# Solid Suspense & SuspenseList — how do fallbacks swap without flicker and how is reveal order coordinated?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What does the Suspense context store object carry, and how does the fallback root avoid re-creating children?

## Suspense.ts: counter store + fallback-root latch
**Path/Symbol:** `packages/solid/src/render/Suspense.ts:Suspense` (:123-212), `SuspenseList` (:35-110), `suspenseListEquals` (:26-27).
**Signature:** `Suspense(props: { fallback?: JSX.Element; children: JSX.Element })`; context value type `{ increment?, decrement?, inFallback?, effects?, resolved? }`.
**Data Shape:** local `counter` number; `store = { increment: ++counter===1→setFallback(true), decrement: --counter===0→setFallback(false), inFallback signal, effects: [], resolved }`; hydration branch keys off `sharedConfig.load(key)` with `"$$f"` marker for pre-rendered fallbacks; `flicker` equals:false signal for one-shot post-hydration nudge.

### Decisive source
```ts
const rendered = createMemo(() => props.children);
return createMemo((prev: JSX.Element) => {
      const inFallback = store.inFallback(),
        { showContent = true, showFallback = true } = show ? show() : {};
      if ((!inFallback || (p && p !== "$$f")) && showContent) {
        store.resolved = true;
        dispose && dispose();
        dispose = ctx = p = undefined;
        resumeEffects(store.effects);
        return rendered();
      }
      if (!showFallback) return;
      if (dispose) return prev;             // ← flicker guard: keep previous fallback
      return createRoot(disposer => {
        dispose = disposer;
        if (ctx) { setHydrateContext({ id: ctx.id + "F", count: 0 }); ctx = undefined; }
        return props.fallback;
      }, owner!);
});
```

**Flow:** resources read under Suspense register via context (`increment`) — first suspension flips `inFallback`; resolution decrements to zero and flips back. The render memo: while suspended, create a ROOT around props.fallback ONCE and reuse it (`if (dispose) return prev`); on resolve, dispose the fallback root, `resumeEffects(store.effects)` runs effects that were parked while suspended (see runTop's suspense branch), and switch to `rendered()`.
**Invariant:** Parked effects are the deadlock-prevention mechanism: computations under a suspending boundary don't run mid-suspension; they queue in `store.effects`. The `prev` latch means rapid suspend/resolve cycles never re-mount fallback DOM. SuspenseList coordinates N children through a registry of `inFallback` accessors with three reveal orders (forwards/backwards/together) + tail modes (collapsed/hidden), using a custom `equals` on registered-state pairs so only real show/hide flips propagate.
**Probe:** `grep -c 'resumeEffects(store.effects);' packages/solid/src/render/Suspense.ts` → `1`; `grep -c 'if (++counter === 1) setFallback(true);' packages/solid/src/render/Suspense.ts` → `1`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "Suspense inFallback resumeEffects SuspenseList revealOrder", limit: 10 });
```

## Verdict
Adopt counter-based context + parked-effects + fallback latch. Adapt hydration id/"F" suffix branches to host hydration. Omit SuspenseList unless orchestrating multiple boundaries.
