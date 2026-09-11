<!-- capsule-v2 -->
# Dynamic-port restart handoff — how does `server.port: 0` keep the SAME port across restarts without leaking it between instances?

**Source:** rsbuild MIT `main@bc19fd5e`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild` (path-slugged twin adopted 2026-08-24 — short-name `rsbuild` serves pre-drift spans). **Question:** a porter must know why port resolution consults a WeakMap keyed by the restart-options object, why strictPort is suppressed while inheriting, and why the inherited port is deleted in a `finally`.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/helper.ts:getPort` (426–494), `resolvePort` (498–520); `packages/core/src/helpers/restartManager.ts` — `restartPorts` WeakMap (22), `setPort` (36–38), `inheritPort` (39–45), expose-window in `requestRestart` (88–98); consumer ladder `packages/core/src/server/devServer.ts` (112–119); `<port>` sentinel `plugins/moduleFederation.ts` (31–36) → substitution `server/assets-middleware/index.ts` (204–206); CLI truthiness fix `cli/init.ts` (84).
**Signature:** `resolvePort(config, lastPort?): Promise<{port:number, portTip?:string}>`; `restartManager.setPort(port): void`; `restartManager.inheritPort(options?): number|undefined`.
**Data Shape:** `restartPorts = WeakMap<object, number>` keyed by the RESTART OPTIONS OBJECT (not the manager, not global); `RestartContext.options = pick(devServerOptions, ['getPortSilently'])` so dev restarts carry a stable key across instance generations.

### Decisive source
```ts
// helper.ts — port 0 is captured from the OS inside the probe, not post-hoc:
const { createServer } = await import('node:net');
const original = port;
let found = false; let attempts = 0;
while (!found && attempts <= tryLimits) {
  try { await new Promise((resolve, reject) => {
    const server = createServer(); server.unref();
    server.on('error', reject);
    server.listen({ port, host }, () => {
      if (port === 0) {                       // ephemeral probe: adopt OS-assigned port
        const address = server.address();
        if (address && typeof address !== 'string') port = address.port;
      }
      found = true; server.close(resolve);
    });
  }); } catch (e) { if (e.code !== 'EADDRINUSE') throw e; port++; attempts++; }
}
```
```ts
// helper.ts — resolvePort: inherit beats config; strictPort applies ONLY when not inheriting
const preferredPort = originalPort === 0 ? lastPort : undefined;
const port = await getPort({
  host,
  port: preferredPort ?? originalPort,
  strictPort: preferredPort === undefined && strictPort,
});
const portTip =
  originalPort !== 0 && port !== originalPort      // never tip on a dynamic port
    ? `port ${originalPort} is in use, ${color.yellow(`using port ${port}.`)}`
    : undefined;
```
```ts
// restartManager.ts — port exposed ONLY while the replacement task is created
if (context.action !== 'dev' || port === undefined) return restart(context);
// Expose the port only while the replacement task is being created.
restartPorts.set(context.options, port);
try { return await restart(context); }
finally { restartPorts.delete(context.options); }   // no leak on failure OR success
```

**Flow:** dev server start reads `config.server.port === 0` → `inheritPort(devServerOptions)` returns (and CONSUMES) any port stashed by the dying instance → `resolvePort(config, lastPort)` prefers the inherited port over a fresh ephemeral probe and suppresses strictPort (a restart onto your own old port must not fail because it's "occupied") → after resolution `setPort(port)` stores it on the CURRENT manager → on watch-triggered restart, `requestRestart` runs onRestart hook + cleanups (swap-first semantics, see `restart-shutdown`), then stashes `port` under `context.options`, calls the user `restart(context)` fn, and deletes the stash in `finally`. The replacement instance's `createDevServer` inherits it — same URL across config-edit restarts. Preview servers never participate (`context.action !== 'dev'`). Module federation providers emit `dev.client.port = '<port>'` when configured as 0 so the CLIENT bundle gets the literal substituted at assets-middleware time (`clientConfig.port === '<port>'` → `resolvedPort`) instead of baking in a dead number. CLI `--port 0` works because `cli/init.ts` tests `options.port !== undefined` (commander default 0 was previously falsy-skipped).

**Invariant:** (1) the handoff key is the OPTIONS OBJECT identity — two managers sharing one restart callback stay isolated (unit-pinned: first.setPort(3000)/second.setPort(4000) inherit [3000,4000] in order); (2) strictPort NEVER fires while inheriting (`preferredPort === undefined && strictPort`) — otherwise every dynamic-port restart would abort claiming the dying server's own port is occupied; (3) the stash lives exactly for the duration of `restart(context)` — leak-free on throw AND success, so a later unrelated restart cannot silently reuse a stale port; (4) `portTip` is suppressed for dynamic ports (OS choice is not "port 0 in use"); (5) `getPort` captures port 0 DURING listen — reading `server.address()` outside the listen callback yields the un-bound 0.

**Probe:** `packages/core/tests/server.test.ts:53-64` (resolvePort port 0 → port > 0 AND portTip undefined even under strictPort:true). `packages/core/tests/restartHook.test.ts:43-59` (per-manager port isolation through shared callback). `e2e/cases/javascript-api/restart-preserve-options/index.test.ts:70-117` (watch-file restart chains a NEW createRsbuild instance and pins `restartResult.port === port` — the full handoff, end to end). `e2e/cases/server/port/index.test.ts:31-70` (hook/context/httpServer.address()/printed URLs/script src ALL report the resolved port). `e2e/cases/cli/port-zero/index.test.ts` (--port 0 boots). `e2e/cases/module-federation/v1-basic/index.test.ts` (remote on port 0 still HMRs through host page).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "resolvePort inheritPort setPort restartPorts getPort", limit: 10 });
```

## Verdict
Adopt the options-object WeakMap handoff, consume-on-read inheritance, strictPort suppression while inheriting, finally-windowed stash lifetime, and the `<port>` client sentinel substituted at middleware setup. Adapt the pick()ed option whitelist (`getPortSilently`) to whatever your restart options struct carries. Omit rsbuild's specific portTip copy/colors. Coverage caveat: the cross-instance e2e runs a user-supplied `restart` callback chain — CI-only path; unit layer covers isolation and port-0 resolution directly.
