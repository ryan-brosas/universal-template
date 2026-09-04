<!-- capsule-v2 -->
# Dev server lifecycle — how does the dev server resolve ports, defer compilation, close exactly-once, and keep restart watchers alive for retry?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the port-probe ladder with strictPort, what `runCompile:false` stubs out, and why closing server resources is memoized separately from closing the restart watcher.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/devServer.ts:createDevServer` (80–469) — `closeServerResources` (213–225), `closeServer`/`restartServer` (228–247), environment API wiring (299–332), listen callback ordering (365–399); port helpers in `server/helper.ts:getPort` (387–451), `resolvePort` (453–473).
**Signature:** `createDevServer(options, createCompiler, config, devServerOptions?): Promise<RsbuildDevServer>`.
**Data Shape:** mutable `state = {fileWatcher?, restartWatcher?, devMiddlewares?, buildManager?}`; `closingPromise?: Promise<void>` latch; RsbuildDevServer exposes `{port, middlewares, environments, httpServer, sockWrite, listen, afterListen, connectWebSocket, close, printUrls, open}`.

### Decisive source
```ts
// Port ladder: net-probe increments on EADDRINUSE only; strictPort limits to a single try
let found = false; let attempts = 0;
while (!found && attempts <= tryLimits) {
  try { await new Promise((resolve, reject) => {
    const server = createServer(); server.unref();
    server.on('error', reject);
    server.listen({ port, host }, () => { found = true; server.close(resolve); });
  }); } catch (e) {
    if (e.code !== 'EADDRINUSE') throw e;
    port++; attempts++;
  }
}
if (!found) throw new Error(`... Failed to find an available port after ${tryLimits + 1} attempts ...`);
```
```ts
// Keep the restart watcher active when closing server resources, so failed restarts can be retried.
const closeServerResources = () => {
  if (!closingPromise) {
    unregisterRestart?.(); unregisterRestart = undefined;
    closingPromise = (async () => {
      removeCleanup(closeServer);            // don't re-run via signal path
      cleanupGracefulShutdown?.();
      await context.hooks.onCloseDevServer.callBatch();
      await Promise.all([state.devMiddlewares?.close(), state.fileWatcher?.close()]);
    })();
  }
  return closingPromise;
};
const restartServer = async () => {
  const restarted = await requestRestart({...});
  if (restarted) { await state.restartWatcher?.close(); }   // only after success
  return restarted;
};
```

**Flow:** resolvePort probes BEFORE anything else and produces `portTip` ("port N is in use, using port M") surfaced unless `getPortSilently`. With default `runCompile:true`, `startCompile()` awaits the shared compiler promise, taps watchRun/done per sub-compiler at stage −10000 to reset/complete compileState, constructs BuildManager (assetsMiddleware + SocketServer), inits it. URL printing is tapped onto `onBeforeCreateCompiler` when compiling (so it lands between listen and first build) or awaited directly otherwise. `listen()` appends the OPTIONS-fallback then not-found middleware INSIDE the listen callback (comment: must be last, PR #2867), attaches the WS upgrade handler, runs `afterListen` → `onAfterStartDevServer.callBatch`, resolves `{port, urls, server}`. `runCompile:false` skips compiler/buildManager entirely and every env-API method throws the "when runCompile is false" error.

**Invariant:** close resources once (latched promise) but never close the restart watcher before a restart succeeds — failed config edits keep watching so the user can fix and retry; middleware registration order (user unshift → internals incl. gzip-after-proxy → user push → history fallback re-adding assets middleware → htmlFallback → favicon → optionsFallback → notFound) is contractual.

**Probe:** `e2e/cases/server/strict-port/index.test.ts:25-45+` pins strictPort throw when occupied; `e2e/cases/server/port/index.test.ts:6-26` pins resolved-port equality and page loads; `tests/restartHook.test.ts:4-27` pins the registry-swap semantics that underpin retryable restarts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createDevServer getPort resolvePort closeServerResources startCompile", limit: 10 });
```

## Verdict
Adopt probe-ladder ports, latched resource close, restart-watcher-outlives-failure, and runCompile stubbing. Adapt tip copy and shortcut wiring. Omit rsbuild's CLI-shortcut keymap except as an extension point example. Coverage caveat: strict-port/port probes are e2e-only upstream.
