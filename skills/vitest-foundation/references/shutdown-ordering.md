<!-- capsule-v2 -->
# Shutdown ordering — in what order must workers, browser pages, Vite servers, and global teardown close to avoid port/session races?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** What is the safe teardown order for a system with worker pools, dev servers, and per-project global setup — and how are teardown errors surfaced?

## Vitest.close
**Path/Symbol:** `packages/vitest/src/node/core.ts:Vitest.close` (1540–1603), `exit` (1609–1642) with the `teardownTimeout` watchdog, and `_setRootConfig` (222–261) which closes the old pool before rebuilding.
**Signature:** `public async close(): Promise<void>` — idempotent via cached `closingPromise`.
**Data Shape:** collects `teardownErrors: unknown[]`; uses `Promise.allSettled` over project/server/hook close promises; every rejection is logged and folded into `_checkUnhandledErrors` (exit code 1 unless `dangerouslyIgnoreUnhandledErrors`).

### Decisive source
```ts
this.closingPromise = (async () => {
  // let an in-flight (re)run settle instead of tearing down under it:
  // its file stats and transforms would race the teardown and reject
  clearTimeout(this._rerunTimer)
  await this.runningPromise?.catch(noop)

  const teardownProjects = [...this.projects]
  if (this.coreWorkspaceProject && !teardownProjects.includes(this.coreWorkspaceProject)) {
    teardownProjects.push(this.coreWorkspaceProject)
  }
  // do teardown before closing the server
  for (const project of teardownProjects.reverse()) {
    await project._teardownGlobalSetup().catch(error => { teardownErrors.push(error) })
  }

  // close the pool (and the browser pages with it) BEFORE the Vite
  // servers: closing a server releases its port while automated pages may
  // still be alive — a page's websocket client would auto-reconnect onto
  // the next server that binds the same port and fail with "Unknown session id"
  if (this.pool) {
    try { await this.pool.close?.() } catch (error) { teardownErrors.push(error) }
    this.pool = undefined
  }

  await Promise.allSettled([...project closes, ..._onClose hooks]).then(results => {
    ...log + _checkUnhandledErrors(every rejection + teardownErrors)...
  })
})()
```

**Flow:** settle in-flight run → reverse-order global teardown (LIFO against setup order; errors collected, never thrown) → pool closed FIRST while servers still hold their ports (comment documents the websocket auto-reconnect "Unknown session id" race this prevents) → projects' Vite servers + user `onClose` hooks in parallel under allSettled → traces finished. `exit()` wraps everything with an unref'd `teardownTimeout` timer that reports `onProcessTimeout`, hints at the hanging-process reporter, and force-exits.

**Invariant:** (1) never tear down under a running test batch; (2) teardown runs in REVERSE registration order and its failures degrade to logged errors + exit code, not crashes; (3) workers/pages die before servers release ports; (4) close is single-shot (cached promise) until a restart resets it.

**Probe:** e2e `test/e2e/test/global-setup.test.ts` (teardown ordering incl. error cases); watch restart tests (`test/e2e/test/watch/restart-coalescing.test.ts`) exercise close→recreate cycles; `test/e2e/test/workspaces.test.ts` covers multi-project close.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "close teardownGlobalSetup closingPromise exit teardownTimeout", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.core.Vitest.close / .exit
```

## Verdict
Adopt the settle→reverse-teardown→workers-before-servers→allSettled ordering verbatim for any host with pooled workers plus long-lived servers. Adapt what "pool" and "server" mean. Omit the browser-port reuse detail (`_harness._browserLastPort`) unless the host has auto-reconnecting browser clients.
