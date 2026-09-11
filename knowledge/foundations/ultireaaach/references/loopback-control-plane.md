<!-- capsule-v2 -->
# Loopback control plane — how does a privileged local API stay unreachable from non-loopback web origins while failing loud on port conflicts?

**Source:** Ultireaaach private workspace `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** a local tool exposes run-control + data APIs to its own web UI; what exact gates keep browser pages from other origins from driving it?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/server.ts:createAppServer` (lines 20-32), origin gate at lines 386-389 with `isLoopbackOrigin` (46-48); composition/shutdown in `packages/app/src/index.ts` (14-30).
**Signature:** `function createAppServer(ctx: AppContext): Server` where `AppContext = { coordinator, bridge, store, httpPort, bridgePort, token }`.
**Data Shape:** one node:http server bound to the literal host `"127.0.0.1"`; every request funnels through `handle(req,res,ctx,webDir)` (graph trace: createAppServer -> handle).

### Decisive source
```ts
server.listen(ctx.httpPort, "127.0.0.1");
server.on("error", (err) => {
  console.error(`[ultireaaach] cannot listen on 127.0.0.1:${ctx.httpPort}: ${err.message}`);
  console.error("[ultireaaach] another instance is probably already running. Kill it (fuser -k " + ctx.httpPort + "/tcp) or set ULTIREAAACH_PORT.");
  process.exit(1);
});
// handle():
if (method !== "GET" && method !== "HEAD") {
  const origin = req.headers.origin;
  if (origin && !isLoopbackOrigin(origin)) { json(res, 403, { error: "forbidden origin" }); return; }
}
function isLoopbackOrigin(o: string): boolean {
  return /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/.test(o);
}
```

**Flow:** bind literal loopback -> per-request URL parse -> non-GET/HEAD requests must carry a loopback Origin or get 403 -> route dispatch. Composition root wires coordinator+bridge+store+token once; SIGINT/SIGTERM shutdown ladder is interrupt -> bridge.close -> server.close -> pas close -> store.close -> exit(0).
**Invariant:** mutating routes are never reachable from a foreign web page's fetch (CSRF fence without cookies); a port conflict kills THIS process loudly instead of silently serving a second instance on another port.
**Probe:** `packages/app/test/li-proxy.test.ts` before() boots the real stack on ephemeral ports and the POST /lh-backend/v2/linkedInAccounts case proves loopback mutation works; run via `pnpm test`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ultireaaach", query: "createAppServer", limit: 5 });
// observed: total 1 -> ultireaaach.packages.app.src.server.createAppServer Function packages/app/src/server.ts 20-32
```

## Verdict
Adopt literal-loopback binding + Origin regex gate + exit(1)-with-hint error ladder for any privileged localhost API. Adapt port/token env names (`ULTIREAAACH_PORT`, `ULTIREAAACH_TOKEN`) and the fuser hint to your platform. Omit nothing security-relevant: dropping the Origin gate reopens CSRF from any browsed page.
