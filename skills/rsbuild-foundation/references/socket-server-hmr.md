<!-- capsule-v2 -->
# Socket server & HMR message protocol — what decides ok / hash / errors / warnings / full-reload per connected token?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the token-authenticated socket registry, the initial-chunk-set reload trigger, and the hash short-circuit ladder order.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/socketServer.ts:upgrade` (174–191), heartbeat `checkSockets` (195–212), `prepare` (222–244), `onBuildDone` (246–257), sendError/sendWarning (262–308), `sendMessage` (316–335), close (337–368), `onConnect` (370–481), `getInitialChunks`/`ensureInitialChunks` (487–527), `getStats` (530–554), `sendStats` (557–612).
**Signature:** `class SocketServer { constructor(context, devConfig, getOutputFileSystem); upgrade; prepare(); onBuildDone(); sendMessage(message, token?); ... }`.
**Data Shape:** `socketsMap: Map<token, Set<WebSocket>>`; `initialChunksMap: Map<token, Set<string>>`; `currentHash: Map<token,string>`; `reportedBrowserLogs: Set<string>`; messages are a closed union (`ok | full-reload{path?} | static-changed | hash{data} | warnings{text[]} | errors{text[],html} | resolved-client-error{id,message} | custom{event,data}`).

### Decisive source
```ts
// auth: reject upgrade unless query token equals one environment's webSocketToken
const tokens = this.context.environmentList.map(({ webSocketToken }) => webSocketToken);
if (!tokens.includes(query.token)) { socket.destroy(); return; }
```
```ts
// decision ladder in sendStats
const newInitialChunks = this.getInitialChunks(stats);
const shouldReload = stats.entrypoints && initialChunks && !isEqualSet(initialChunks, newInitialChunks);
this.initialChunksMap.set(token, newInitialChunks);
if (shouldReload) { this.sendMessage({ type: 'full-reload' }, token); return; }  // web-infra-dev/rspack#6633
if (stats.hash) {
  const prevHash = this.currentHash.get(token);
  this.currentHash.set(token, stats.hash);
  if (!force && errors.length === 0 && warnings.length === 0 && prevHash === stats.hash) {
    this.sendMessage({ type: 'ok' }, token); return;      // nothing changed → bare ok
  }
  this.sendMessage({ type: 'hash', data: stats.hash }, token);
}
if (errors.length > 0) { this.sendError(errors, token); return; }
if (warnings.length > 0) { this.sendWarning(warnings, token); return; }
this.sendMessage({ type: 'ok' }, token);
```
```ts
// per-env stats slice but GLOBAL error/warning aggregation
if (stats.children) { const child = stats.children[environment.index]; if (child) currentStats = child; }
return { stats: currentStats, errors: getStatsErrors(stats), warnings: getStatsWarnings(stats) };
```

**Flow:** prepare() creates a noServer WSS bound to optional client path and starts an unref'd 30s heartbeat that terminates sockets failing one pong. onConnect registers pong-alive, parses client messages inside try/catch-ignore, routes `client-error` only when buildState has no build errors AND browserLogs enabled — formatting via stacktrace-parser + trace-mapping with a per-connection CachedTraceMap, deduplicating identical logs through reportedBrowserLogs (cleared each onBuildDone), and optionally echoing `resolved-client-error` with rendered HTML when runtime overlay passes its filter. Sockets are tracked per-token; close prunes empty sets. ensureInitialChunks snapshots entrypoint chunk sets even with zero clients so first comparison after connect is stable. Overlay HTML for compile errors is produced by filtering through user `overlay.errors(Error)` predicates then `renderErrorToHtml`.

**Invariant:** every send is token-scoped (broadcast only when token omitted by explicit API users like sockWrite('*')); initial-chunk comparison must use set-equality (order-insensitive) or polyfill additions would loop reloads.

**Probe:** `e2e/cases/javascript-api/sock-write/index.test.ts:4-32` pins full-reload/static-changed/path-scoped reload observable behavior; `e2e/cases/hmr/live-reload/index.test.ts:5-25+` pins liveReload:false suppressing reload; `e2e/cases/server/reload-html/index.test.ts:5-17` pins html-template invalid → full-reload path from setupServerHooks. Direct unit tests absent upstream for sendStats ladder (coverage caveat: deterministic source read).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "SocketServer sendStats onBuildDone ensureInitialChunks upgrade checkSockets", limit: 10 });
```

## Verdict
Adopt token-scoped fan-out, chunk-set-change full reload, and the hash short-circuit ladder as the portable HMR protocol core. Adapt message names/payloads to host client. Omit rsbuild's overlay rendering internals beyond the filter hook point. Coverage caveat: protocol ladder verified by source + e2e citations, not executed here.
