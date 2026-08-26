<!-- capsule-v2 -->
# Extension bridge bootstrap — how does an unpacked MV3 extension discover and authenticate to a per-launch local service?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** the service regenerates its token every launch; how does the extension learn port+token and hold exactly one authenticated socket?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/bridge.ts:ExtensionBridge.onConnection` (42-55) + `packages/extension/background.js` bootstrap ladder (49-62).
**Signature:** server: `new WebSocketServer({ port, host: "127.0.0.1" })`; client: `new WebSocket("ws://127.0.0.1:" + BRIDGE_PORT + "/?token=" + token)`.
**Data Shape:** discovery doc `GET /api/bridge-info -> { port, token }`; command envelope `{type:"exec", id, tabId?, payload:{op,...}}`; result envelope `{type:"exec-result", id, result?|error?}`.

### Decisive source
```ts
private onConnection(ws: WebSocket, req: IncomingMessage): void {
  const url = new URL(req.url ?? "/", "http://127.0.0.1");
  const token = url.searchParams.get("token");
  if (token !== this.token) { ws.close(4001, "invalid token"); return; }
  this.socket = ws;                      // single slot: latest connection wins
  ws.on("close", () => { if (this.socket === ws) this.socket = null; });
}
send(msg: object): boolean {
  if (this.socket && this.socket.readyState === WebSocket.OPEN) { this.socket.send(JSON.stringify(msg)); return true; }
  return false;
}
```
```js
// background.js: fetch http://127.0.0.1:4789/api/bridge-info -> token -> connect;
// EVERY failure path schedules retry:
ws.onclose = () => { ws = null; setTimeout(bootstrap, 2000); };
catch (e) { setTimeout(bootstrap, 2000); }   // constructor throw AND fetch failure
```
**Flow:** service starts with random 24-byte hex token (dev pins ULTIREAAACH_TOKEN) -> extension service worker boots on startup/install/immediate -> GET bridge-info -> WS connect with ?token= -> server validates, replaces socket slot -> exec envelopes route via chrome.tabs.sendMessage to content scripts -> results correlated by id; any drop/failure retries in 2s forever.
**Invariant:** token never embedded in extension code (per-launch discovery); auth failure is close(4001) not silent; send() reports false instead of throwing when disconnected; content scripts stay GENERIC DOM ops (ping/pageState/exists/readText/readAttr/click/waitVisible polling offsetParent at 200ms) with all selector knowledge server-side (ADR-006/007).
**Probe:** handshake documented by `packages/app/test/bridge-integration.mjs` but that script is STALE (calls a removed createAppServer signature) — recorded blocker; deterministic checks this pass: token-mismatch close code 4001 read directly from source, connected-flag flip asserted indirectly by li-proxy.test.ts stack boot. See verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ultireaaach", query: "ExtensionBridge token", limit: 5 });
// observed: top hits constructor(30-40)/send(67-73)/connected(75-77)/onConnection(42-55) in packages/app/src/bridge.ts
```

## Verdict
Adopt discovery-doc + query-token WS auth + single-slot socket + unconditional retry ladder for local tool <-> extension pairs. Adapt envelope vocabulary to your op set. Omit the LH exec routing (M0 log-only placeholder) until you define real ops; keep generic content-script primitives so selectors never ship in the extension.
