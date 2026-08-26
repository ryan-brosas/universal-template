<!-- capsule-v2 -->
# Async hook engine — how do the tap/callChain/callBatch primitives thread results and filter taps by environment?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know exactly when a callback's return value mutates the next call (and when it doesn't), and why environment hooks still run global taps.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/hooks.ts:createEnvironmentAsyncHook` (33–136), `createAsyncHook` (138–186), `initHooks` (188–240).
**Signature:** `createAsyncHook<Callback>(): AsyncHook<Callback>` with `tap`, `callChain(...args): Promise<Parameters<Callback>>`, `callBatch(...args): Promise<T[]>`; env variant wraps args in `{environment?, args, afterEach?}`.
**Data Shape:** three internal buckets — `preGroup`, `defaultGroup`, `postGroup` — populated at tap time from either a bare function (default) or a `{handler, order}` descriptor; call sites re-concat `[...preGroup, ...defaultGroup, ...postGroup]` so ordering is fixed at CALL time, not tap time. 14 global hooks + 8 environment-scoped hooks are instantiated by `initHooks` (`modifyHTML/modifyHTMLTags/modifyRspackConfig/modifyBundlerChain/modifyEnvironmentConfig/onBefore|AfterEnvironmentCompile`).

### Decisive source
```ts
// createAsyncHook.callChain: result REPLACES params[0] only when defined
for (const callback of callbacks) {
  const result = await callback(...params);
  if (result !== undefined) { params[0] = result; }
}
return params;
```
```ts
// createEnvironmentAsyncHook.callChain: env filtering + afterEach hook
const callbacks = [...preGroup, ...defaultGroup, ...postGroup];
for (const callback of callbacks) {
  // If this callback is not a global callback, the environment info should match
  if (environment && callback.environment && callback.environment !== environment) continue;
  const result = await callback.handler(...params);
  if (result !== undefined) { params[0] = result; }
  if (afterEach) { afterEach(params); }
}
return params;   // note: returns the ARGS ARRAY, not a single value
```

**Flow:** `tap(cb | {handler, order})` routes into pre/default/post; `callChain` executes serially awaiting each handler; a returned value other than `undefined` becomes the first argument for subsequent handlers (config-modification semantics), while event-style hooks simply return void and pass originals through; `callBatch` runs the same sequence but never threads results — it collects every return into an array (used for hooks where each tap contributes independently, e.g. `onBeforeStartDevServer` returning post-callbacks). Environment hooks add per-tap environment tagging: when invoked with an `environment`, global taps (environment undefined) always run and tagged taps run only on match.

**Invariant:** hook execution order is deterministic pre→default→post regardless of tap interleaving; `undefined` is strictly "no change" — a porter that forwards `null` or lets handlers return promises-of-void breaks both contracts. `callChain`'s return is the full parameter tuple, so callers destructure `const [modified] = await hook.callChain(config)`.

**Probe:** `tests/createAsyncHook.test.ts:40-87` pins mixed-order execution `[5,6,1,4,7,2,3]`; `:89-105` pins first-param threading ("second: modified message"); `:107-121` pins batch collection without threading. `tests/hooks.test.ts:10-35` pins env filtering: global tap fires for both 'a' and 'b', tagged tap only for 'a'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createAsyncHook createEnvironmentAsyncHook initHooks callChain callBatch", limit: 10 });
```

## Verdict
Adopt the bucketed tap model, undefined-means-no-change threading, batch collection, and environment-tagged taps as the portable lifecycle primitive (~90 lines, zero deps). Adapt hook name sets to host needs. Omit Tapable-style interception/waterfall variants rsbuild does not use. Coverage caveat: probes verified against on-disk rstest specs, not executed this run.
