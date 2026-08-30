<!-- capsule-v2 -->
# Effect runtime escape hatches — how do you call a Layer-built service from non-Effect code?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** when a subsystem must be callable from plain async code (npm install, CLI paths), how do you embed an Effect service without duplicating layer instances or losing the typed method surface?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/effect/runtime.ts`: `makeRuntime` (:4-21); `packages/core/src/effect/service-use.ts`: `serviceUse` (:17-43); `packages/core/src/effect/memo-map.ts` (:1-3).
**Signature:** `makeRuntime<I, S, E>(service: Context.Service<I, S>, layer: Layer.Layer<I, E>) => { runSync, runPromise, runPromiseExit, runFork, runCallback }`; `serviceUse<Identifier, Shape>(tag) => ServiceUse<Identifier, Shape>` (Proxy).
**Data Shape:** one module-level `memoMap = Layer.makeMemoMapUnsafe()` shared by every makeRuntime caller; the runtime itself is a lazily assigned `rt ??= ManagedRuntime.make(...)`.

### Decisive source
```ts
const getRuntime = () =>
  (rt ??= ManagedRuntime.make(Layer.provideMerge(layer, Observability.layer) as Layer.Layer<I, E>, {
    memoMap,
  }))
...
runPromise: <A, Err>(fn: (svc: S) => Effect.Effect<A, Err, I>, options?) =>
  getRuntime().runPromise(service.use(fn), options),
```

**Flow:** first call builds the ManagedRuntime (provideMerge Observability.layer, shared memoMap) and caches it → every run* wraps the caller's function in `service.use(fn)` → subsequent calls reuse the runtime. `serviceUse(tag)` returns a Proxy; each string property resolves to a per-key cached accessor `(...args) => tag.use(svc => svc[key](...args))`; the `ServiceUse` mapped type keeps only Effect-returning methods, and a non-function method dies with `Service method not found: <key>`.
**Invariant:** the memoMap is process-wide — two makeRuntime call sites sharing a layer get ONE memoized instance, not two; the Proxy is the single documented dynamic boundary (runtime key checks are values TypeScript cannot see).
**Probe:** no direct unit test pins makeRuntime/serviceUse (coverage caveat: source-confirmed; the only src consumer of makeRuntime is `npm.ts:257` `const { runPromise } = makeRuntime(Service, LayerNode.compile(node))`, and of serviceUse is `fs-util.ts:51` `export const use = serviceUse(Service)` — both verified by grep at this pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "makeRuntime ManagedRuntime serviceUse proxy accessor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy-runtime-over-shared-memoMap pattern whenever an Effect service must be reachable from non-Effect code, and the typed-Proxy accessor for ergonomic service access with per-key caching. Adapt the Observability provideMerge to your host's telemetry layer. Omit nothing — both files are 21L/43L and self-contained. Coverage caveat: no direct test; the two consumers above are the evidence.
