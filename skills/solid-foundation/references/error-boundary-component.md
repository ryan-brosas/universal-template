<!-- capsule-v2 -->
# Solid ErrorBoundary — how is the boundary itself a memo that catches its own children's errors via catchError?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** How does client-side ErrorBoundary reset work, and how do errors thrown in fallbacks reach parent boundaries?

## flow.ts ErrorBoundary + module-level Errors set
**Path/Symbol:** `packages/solid/src/render/flow.ts:ErrorBoundary` (:273-297), `resetErrorBoundaries` (:255-257).
**Signature:** `ErrorBoundary(props: { fallback: JSX.Element | ((err: any, reset: () => void) => JSX.Element); children: JSX.Element }): JSX.Element`.
**Data Shape:** module singleton `Errors: Set<Setter<any>>` — every mounted boundary registers its `setErrored`; SSR seeds initial error from `sharedConfig.load(getContextId())`.

### Decisive source
```ts
Errors || (Errors = new Set());
Errors.add(setErrored);
onCleanup(() => Errors.delete(setErrored));
return createMemo(() => {
      let e: any;
      if ((e = errored())) {
        const f = props.fallback;
        if (IS_DEV && (typeof f !== "function" || f.length == 0)) console.error(e);
        return typeof f === "function" && f.length ? untrack(() => f(e, () => setErrored())) : f;
      }
      return catchError(() => props.children, setErrored);
});
```

**Flow:** each render pass re-runs children INSIDE `catchError` — a throw anywhere below routes to `setErrored`, which flips the same memo to fallback mode. The reset callback passed to functional fallbacks IS `setErrored(undefined)`-style clearing, so clicking "retry" re-enters children. `resetErrorBoundaries()` clears EVERY mounted boundary at once.
**Invariant:** Boundary nesting falls out of catchError's owner-chain handler walk (see error-boundaries capsule): a throw inside a fallback propagates to the PARENT boundary because this boundary's memo has no handler around its own body. The dev-only console.error fires only for non-functional fallbacks (functional ones are assumed to display it).
**Probe:** `grep -c 'return catchError(() => props.children, setErrored);' packages/solid/src/render/flow.ts` → `1`. Behavior pinned by test/rendering.spec.ts and signals.spec "catchError" family; server twin behavior (serialize + replace) pinned by test/server/lazy.spec.ts (:38-94).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "ErrorBoundary errored resetErrorBoundaries", limit: 10 });
```

## Verdict
Adopt memo-self-catch structure (no extra primitives needed). Adapt the Errors registry to host (it exists for global resets only). Omit SSR seed branch until hydration.
