<!-- capsule-v2 -->
# PAS launcher-RPC shim — how do you impersonate a desktop launcher's Socket.IO surface so a vendored SPA boots locally?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** an Electron-targeted webapp expects a native launcher process speaking Socket.IO RPC on localhost:4000 — what does a total shim look like?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/pas-server.ts` — `createPasServer` (12-44), `handleRpc` (48-76), `handleMainWindow` (78-111), `specificResult` (113-170), `smartDefault` (172-204), `httpHandler` (206-222). Graph ownership: trace_path outbound createPasServer -> callees_total 9 (handleMainWindow ×2, handleRpc, httpHandler, json ×2, smartDefault, specificResult ×2 + vendored-bundle noise).
**Signature:** `createPasServer(opts: {port, coordinator, store}) -> {io, httpServer}`; `handleRpc(method, args): Promise<unknown>`; `specificResult(name, payload): unknown`.
**Data Shape:** rpc envelope `{id:number, method:string, args:unknown[]}` answered either via ack callback `{id, result|error}` or by emitting `rpc:result` with the same shape; `requestActionAtLauncher*` results are double-wrapped as `{responseEncoded: JSON.stringify(result)|null, error:null}`.

### Decisive source
```ts
socket.on("rpc", (msg, cb?) => {
  handleRpc(msg.method, msg.args)
    .then((result) => { if (cb) cb({ id: msg.id, result }); else socket.emit("rpc:result", { id: msg.id, result }); })
    .catch((error) => { /* same duality with { id, error } */ });
});
socket.on("ipc:invoke", ({ id, channel }) =>
  socket.emit("ipc:invoke:result", { id, result: smartDefault(channel) })); // ALWAYS emits, never acks
```
`handleRpc` routing ladder: `mainWindow.*` -> strip prefix into `handleMainWindow`; any method CONTAINING `getInstanceProfile` -> FAKE_LI profile (`cloudLicenseEnabled:false`, `liAccessLevel:4`); `__source.` paths unwrap `args[0]` as the real source-method name for `.callRead/.callWrite` (else treat the path itself as the method); `__db*` -> null; default -> `smartDefault(method)`. `handleMainWindow` arg-shape ladder: JSON string `{name,payload}` | bare string + `args.slice(1)` | object `{name,payloadJsonable}`.
**Flow:** SPA -> socket.io connect (CORS `*`, allowEIO3) -> rpc/ipc events -> routing ladder -> `specificResult` switch (~45 fixture cases: machine/license/campaign fixtures + window ops show/hide/focus/isVisible/callWindow) -> fallback `smartDefault`. A SECOND HTTP plane rides the same port (`httpHandler`): `/env/public`, `/authTokens`, `/licenses`, `/frontendSettings`, `/users`, `[]` families (orders/subscriptions/billingInfos/linkedInAccounts/newInstances/lists/proxies), `/pas/credits {credits:1000}`, default `{ok:true}` — CORS `*` + OPTIONS short-circuit and NO Origin gate; the 127.0.0.1 bind is the only fence (contrast the app server's loopback-Origin gate).
**Invariant:** the shim NEVER rejects — every method resolves to a fixture or a type-plausible default, because one thrown "method not found" kills SPA bootstrap. Port-conflict policy is fail-loud: listen error prints a `fuser -k <port>/tcp` hint and `process.exit(1)` (37-41). Caveat: JS switch labels here are NOT unique keys — `case "isVisible"` appears twice (window-op group and after getUILayout) and `getCampaignsInfo` twice; first-match-wins makes it harmless but don't extract the switch into a map assuming uniqueness.
**Probe:** no upstream unit test exists for pas-server.ts (coverage caveat). Deterministic probes executed this pass: `pnpm test` in packages/app exit 0 (9/9 — the li-proxy suite boots the REAL app stack incl. mock planes); graph probe trace_path createPasServer returned the exact 9-callee fanout above; byte-anchors line-checked against the checkout read of pas-server.ts 1-47/48-76/78-111/113-170/206-222.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ultireaaach", query: "createPasServer PAS launcher rpc shim" });
// observed this pass: total 108, top hits createPasServer(12-44), handleRpc(48-76),
// front/build/electron-bridge.launcherRpcCall(91-98), specificResult(113-170), smartDefault(172-204)
```

## Verdict
Adopt the envelope-duality discipline: answer through the ack when the client passed one, emit a namespaced result event otherwise, and wrap legacy `requestActionAtLauncher` payloads exactly as the consumer unwraps them (`responseEncoded` JSON string). Adapt the fixture table to your own launcher's method vocabulary. Omit the LH machine/license fixtures; keep the never-reject floor via a total name heuristic (see smart-default-total-mock).
