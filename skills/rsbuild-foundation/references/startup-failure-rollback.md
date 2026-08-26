<!-- capsule-v2 -->
# Startup-failure rollback — how do dev/preview servers guarantee the port is released and close hooks run when startup throws?

**Source:** rsbuild MIT `main@bc19fd5e`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild` (path-slugged twin adopted 2026-08-24). **Question:** a porter must know why `listen()` is awaited via `once(httpServer,'listening')` inside try/catch, why rollback calls the SAME memoized close path as normal shutdown, and why a failing close must not mask the original error.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/devServer.ts` — listen try/catch (399–437), `closeServerResources` (213–225), `closeServer` (228–231); `packages/core/src/server/previewServer.ts` — listen try/catch (249–301), `closeServer` close-once latch (88–99); shared terminator `server/helper.ts:getServerTerminator` (634–669); event-driven listen replaces callback-throw `git 7f23f15`, cleanup-after-failure `git 0ea4a17`.
**Signature:** `listen(): Promise<StartDevServerResult>`; `getServerTerminator(server): () => Promise<void>`.
**Data Shape:** `closingPromise?: Promise<void>` single-flight latch; terminator tracks `listened: boolean` + `pendingSockets: Set<Socket>`.

### Decisive source
```ts
// devServer.ts listen() — awaitable listen, full rollback on ANY startup failure:
try {
  httpServer.listen({ host, port });
  await once(httpServer, 'listening');        // EADDRINUSE/etc. REJECTS here now
  middlewares.use(optionsFallbackMiddleware); // must be last (PR #2867)
  middlewares.use(notFoundMiddleware);
  if (state.devMiddlewares) httpServer.on('upgrade', state.devMiddlewares.onUpgrade);
  await devServer.afterListen();              // onAfterStartDevServer hooks CAN throw
  return { port, urls, server: devServer };
} catch (error) {
  try { await closeServer(); }                // release port + run onCloseDevServer
  catch (closeError) {
    logger.error('Failed to close dev server after startup error.');
    logger.error(closeError);                 // logged, NEVER thrown over `error`
  }
  throw error;                                // ORIGINAL failure propagates
}
```
```ts
// helper.ts — terminator destroys sockets FIRST, then closes only if it ever listened
return () => new Promise<void>((resolve, reject) => {
  for (const socket of pendingSockets) socket.destroy();
  if (listened) { server.close((err) => err ? reject(err) : resolve()); }
  else { resolve(); }                          // never-listened close would ERR_INVALID_HANDLE-style throw
});
```

**Flow:** before this pair of fixes, `listen()` wrapped everything in `new Promise((resolve) => httpServer.listen({...}, async (err) => { if (err) throw err; ... }))` — a throw inside the listen callback was an UNHANDLED rejection: startDevServer never rejected, the process hung, the port stayed bound, onCloseDevServer never ran. Now listen is fire-and-await (`once(httpServer,'listening')`), so bind errors surface as an ordinary rejection of `listen()`. The catch block reuses the production close path — dev: latched `closeServerResources` (onCloseDevServer.callBatch + devMiddlewares.close + fileWatcher.close, restart watcher deliberately NOT closed so a failed restart can be retried) then `throw error`; preview: latched `closeServer` (removeCleanup + graceful-shutdown teardown + serverTerminator). The e2e pins the exact contract at BOTH layers: a plugin throwing inside `onAfterStartDevServer` rejects `startDevServer()`, runs `onCloseDevServer`, AND frees the port (independent net-probe succeeds).

**Invariant:** (1) rollback is the SAME code path as graceful shutdown — no parallel "abort" teardown that could drift; (2) close-during-rollback errors are demoted to logs; the ORIGINAL startup error is what callers see (double-failure precedence); (3) the terminator's destroy-sockets-before-close ordering makes close deterministic even with keep-alive connections open; (4) closing a server that never bound must resolve, not throw (guarded by `listened`); (5) middleware tail registration stays INSIDE the post-listen window — registering fallbacks before listening would 404-flush early requests.

**Probe:** `e2e/cases/plugin-api/plugin-hooks/index.test.ts:141-166` ('should close dev server when onAfterStartDevServer throws': rejects.toThrow + closeHookCalled===true + expectPortAvailable(port)); `:168-211` mirrors for preview. Direct unit layer for the terminator itself is absent at pin — behavior pinned through these two e2e suites plus `build-manager-shutdown` capsule's shutdown-order coverage.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "getServerTerminator once listening closeServer afterListen notFoundMiddleware", limit: 10 });
```

## Verdict
Adopt: awaitable `once(server,'listening')` pattern, rollback-via-production-close-path, original-error precedence over close errors, destroy-sockets-then-close terminator with never-listened guard. Adapt hook names/onCloseDevServer batching to your host lifecycle. Omit rsbuild's specific logger copy. Coverage caveat recorded above (terminator unit layer absent at pin).
