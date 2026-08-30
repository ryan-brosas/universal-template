<!-- capsule-v2 -->
# Solid SSR streaming — how do Suspense fragments, lazy blocks, and resources serialize into a resumable stream?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** How does the server coordinate placeholder markers, out-of-order flushes, and error serialization?

## server/rendering.ts: Suspense fragments + resource registry + lazy block()
**Path/Symbol:** `packages/solid/src/server/rendering.ts:Suspense` (:675-736), `createResource` (:436-554), `lazy` (:556-608), `ErrorBoundary` (:341-372), `notifySuspense` (:617-625).
**Signature:** `HydrationContext { serialize(id, v, deferStream?), replace(id, fn), block(p), registerFragment(id), resources, suspense, lazy, async?, noHydrate }` — supplied by solid-js/web's renderToStream.
**Data Shape:** per-Suspense id → `ctx.suspense[id] = { resources: Map<string, {_loading, error}>, completed() }`; placeholder HTML `<template id="pl-${id}"></template>${fallback}<!--pl-${id}-->`; ErrorBoundary emits `<!--!$e${id}-->…<!--!$/e${id}-->`.

### Decisive source
```ts
done = ctx.async ? ctx.registerFragment(id) : undefined;
return catchError(() => {
    if (ctx.async) {
      setHydrateContext({ ...ctx, count: 0, id: ctx.id + "0F", noHydrate: true });
      const res = { t: `<template id="pl-${id}"></template>${resolveSSRNode(
          escape(props.fallback))}<!--pl-${id}-->` };
      setHydrateContext(ctx);
      return res;
    }
    setHydrateContext({ ...ctx, count: 0, id: ctx.id + "0F" });
    ctx.serialize(id, "$$f");     // non-async: marker only, client resolves later
    return props.fallback;
}, suspenseError);
```

**Flow:** Suspense renders children once under its owner; if incomplete (`suspenseComplete` scans the resource map for `_loading`) it either registers an out-of-order fragment (async streaming: real content replaces the template marker when `completed()` fires `done(html)`) or serializes `"$$f"` (client waits). Resources store resolved data at `ctx.resources[id].data` so client hydration reads them by id without refetching; promises are handed to `ctx.serialize(id, p, deferStream)` for stream flushing. Lazy components call `ctx.block(promise)` to hold the stream and retry on next REQUEST after rejection (failed module promise is dropped: `if (p === cur) p = undefined`).
**Invariant:** Every branch must keep the hydration ID COUNTER deterministic: both fallback paths reset context with `{...ctx, count: 0}` and suffix ids ("0F"/+"F") so client-side traversal allocates identical ids. ErrorBoundary's `displayFallback` calls `ctx.serialize(id, error)` — errors ARE serialized for client replay. Rejected lazy modules must NOT cache the failure across requests (lazy.spec "rejected module is retried on the next request", :64-93).
**Probe:** `grep -c 'ctx.serialize(id, "$$f");' packages/solid/src/server/rendering.ts` → `1`. Behavior pinned by test/server/lazy.spec.ts (stream end + boundary render + retry semantics).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "registerFragment serialize notifySuspense block lazy", limit: 10 });
```

## Verdict
Adopt marker-template + fragment-registration streaming shape. Adapt marker syntax/escape helpers to host. Omit deferStream nuance until you port stream flushing.
