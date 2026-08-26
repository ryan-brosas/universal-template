<!-- capsule-v2 -->
# HMR client — how does the browser client apply updates, fall back to reload, reconnect, and report runtime errors?

**Source:** rsbuild MIT `main@bc19fd5e` (pass-3 repair: formatURL gains a searchParams prototype guard, 8d8a47d); Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild` (path-slugged twin adopted 2026-08-24). **Question:** a porter must know the BUILD_HASH sentinel mechanism, the idle-state gate before hot.check, exponential reconnect with direct-fallback, the per-module custom-listener GC, and the URL-capability probe before searchParams use.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/client/hmr.ts:formatURL` (105–125), handleSuccess/Warnings/Errors (140–184), handleResolvedClientError (186–208), `shouldUpdate`/tryApplyUpdates (212–256), onOpen/onMessage (269–333), onClose/onSocketError (335–363), sendError (365–382), fullReload (432–453), `setupCustomHMRListeners` (44–71).
**Signature:** `init(token, config, serverHost, serverPort, serverBase, liveReload, browserLogs, logLevel, resolveWebSocketUrl?): void`.
**Data Shape:** closure state `lastHash`, `hasBuildErrors`, `queuedMessages: ClientMessage[]`, `clientErrors: {id,message?}[]`, `customListenersMap`, `reconnectCount`; `BUILD_HASH` is a compile-time placeholder replaced by `import.meta.rspackHash` at client build time.

### Decisive source
```ts
// update gate: lastHash starts as the BUILD HASH sentinel — first real hash message differs → update
const shouldUpdate = () => lastHash !== BUILD_HASH;
function tryApplyUpdates() {
  if (!shouldUpdate()) return;
  if (import.meta.webpackHot) {
    if (import.meta.webpackHot.status() !== 'idle') return;   // Rspack disallows updates mid-cycle
    import.meta.webpackHot.check(true).then(
      (updatedModules) => handleApplyUpdates(null, updatedModules),
      (err) => handleApplyUpdates(err, null));
    return;
  }
  fullReload();   // no HMR plugin registered → hard reload fallback
}
const handleApplyUpdates = (err, updatedModules) => {
  const forcedReload = err || !updatedModules;
  if (forcedReload) { if (err) logger.error('[rsbuild] HMR update failed, performing full reload:', err); fullReload(); return; }
  tryApplyUpdates();   // a newer update arrived while applying → loop again
};
```
```ts
// reconnect: 1.5^n backoff capped by config.reconnect; error path tries DIRECT host once
socket.addEventListener('close', onClose);
function onClose() {
  if (reconnectCount >= config.reconnect) { ...; return; }
  removeListeners(); socket = null; reconnectCount++;
  setTimeout(connect, 1000 * 1.5 ** reconnectCount);
}
```
```ts
// pass-3 repair (8d8a47d): capability-probe searchParams, not just the URL constructor —
// legacy WebKit exposes URL but LACKS searchParams, so `new URL(...)` alone still crashed:
if (typeof URL !== 'undefined' && 'searchParams' in URL.prototype) {
  const url = new URL('http://localhost');
  url.port = String(port); url.hostname = hostname; url.protocol = protocol;
  url.pathname = pathname; url.searchParams.append('token', token);
  return url.toString();
}
// compatible with IE 11 and legacy WebKit where URL lacks searchParams
const colon = protocol.indexOf(':') === -1 ? ':' : '';
return `${protocol}${colon}//${hostname}:${port}${pathname}?token=${token}`;
```
```ts
// per-module listener GC: patched module.hot.on records into both maps; dispose removes exactly those fns
RSPACK_INTERCEPT_MODULE_EXECUTION.push(({ module }) => {
  const newListeners = new Map();
  module.hot.on = (event, cb) => { addToMap(customListenersMap, event, cb); addToMap(newListeners, event, cb); };
  module.hot.dispose(() => { for (const [event, stale] of newListeners) {
    customListenersMap.set(event, customListenersMap.get(event).filter(l => !stale.includes(l))); } });
});
```

**Flow:** init wires window error/unhandledrejection reporters when browserLogs enabled (errors queued while socket closed, flushed on open), connects with token query param. Message switch: hash→update lastHash + clear overlay if changed; ok→clearBuildErrors+tryApplyUpdates; errors→log all + overlay unless `overlay.errors === false`; resolved-client-error→overlay runtime list (never while build failed). Client-error ids are time36+rand36 so the server can patch message text later. full-reload honors `{path}` matching only `.html` paths against location.pathname variants (with base prefix, extensionless, index.html).

**Invariant:** never call hot.check outside idle state; queued client messages must flush in order on open; overlay must not show runtime errors during build failures (server and client both enforce this independently).

**Probe:** `e2e/cases/hmr/remove-module/index.test.ts` and `e2e/cases/hmr/unaffected-environment/index.test.ts` exercise module disposal/update scoping through real page edits; `e2e/cases/hmr/websocket-url-resolver/index.test.ts:23-32` pins resolveWebSocketUrl rewriting plus successful hot swap after edit. No isolated unit tests for hmr.ts (coverage caveat: e2e-level evidence cited from disk).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "hmr tryApplyUpdates shouldUpdate setupCustomHMRListeners getSocketURL fullReload", limit: 10 });
```

## Verdict
Adopt sentinel-hash update gate, idle-gated check loop, backoff reconnect with single direct-host fallback, capability-probe (`'searchParams' in URL.prototype`) before URL-API use with manual string fallback, and dispose-scoped custom listeners. Adapt overlay DOM (separate capsule concern) and message names. Omit IE11/legacy-WebKit URL branch unless targeting legacy browsers. Coverage caveat: e2e-cited only.
