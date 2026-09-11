<!-- capsule-v2 -->
# MCP client fleet lifecycle — how do you manage a fleet of heterogeneous external tool-server connections (stdio + HTTP) with auth failures, liveness, and clean process teardown?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A coding agent connects to N external MCP servers (local stdio processes and remote HTTP endpoints), some requiring OAuth. The fleet must report per-server status, re-list tools when a server changes its tool list, and kill every spawned process on shutdown — without leaking transports or orphaning grandchildren.

## Transport ladder with auth-error classification
**Path/Symbol:** `packages/opencode/src/mcp/index.ts` (`connectTransport` :218-232, `connectRemote` :236-337, `connectLocal` :340-370, `create` :372-416) + `packages/opencode/src/mcp/catalog.ts` (`paginate` :18-36, `listTools` :145-162, `TolerantListToolsResultSchema` :15-17).
**Signature:** `create(key, mcp: ConfigMCPV1.Info) → Effect<CreateResult>`; `CreateResult = {mcpClient?, status: Status, defs?, instructions?}`; `Status = connected | disabled | failed{error} | needs_auth | needs_client_registration{error}`.
**Data Shape:** remote config `{type:"remote", url, headers?, timeout?, oauth?: false|{clientId, clientSecret, scope, callbackPort, redirectUri}}`; local `{type:"local", command: string[], cwd?, environment?, timeout?}`; default timeout 30s (catalog.ts :11).

### Decisive source
```ts
// mcp/index.ts:220-231 — ownership transfer: close the transport ONLY on failure exit
return yield* Effect.acquireUseRelease(
  Effect.succeed(transport),
  (t) => Effect.tryPromise({ try: () => { const client = createClient(directory); return withTimeout(client.connect(t), timeout)... } }),
  (t, exit) => (Exit.isFailure(exit) ? Effect.tryPromise(() => t.close()).pipe(Effect.ignore) : Effect.void),
)
// mcp/index.ts:296-331 — classification inside the catch:
const isAuthError = error instanceof UnauthorizedError || (authProvider && lastError.message.includes("OAuth"))
if (isAuthError) {
  if (lastError.message.includes("registration") || lastError.message.includes("client_id")) {
    lastStatus = { status: "needs_client_registration" as const, error: "Server does not support dynamic client registration..." }
  } else { pendingOAuthTransports.set(key, { transport }); lastStatus = { status: "needs_auth" as const } }
}
lastStatus = { status: "failed" as const, error: lastError.message }
// mcp/index.ts:331 — after an auth-classified failure, stop trying other transports
if (lastStatus?.status === "needs_auth" || lastStatus?.status === "needs_client_registration") break
```

**Flow:** `create()` short-circuits disabled configs to DISABLED_RESULT without connecting. Remote: try StreamableHTTP first, then SSE, both sharing the same authProvider + headers; each attempt goes through `connectTransport` (acquireUseRelease: acquire = new Client + timed connect; release closes only on failure exit). Auth errors classify into needs_client_registration (message mentions registration/client_id → toast tells the user to add clientId) or needs_auth (the failed transport is stashed in module-level `pendingOAuthTransports` for a later finishAuth); either breaks the ladder. Non-auth errors fall through to the next transport; final status is the last error. Local: StdioClientTransport with cwd resolved against the instance directory, env = process.env + `BUN_BE_BUN:"1"` for self-spawned "opencode" commands + user env. After a successful connect, tools are listed only when the server advertises the tools capability; ANY post-connect defect closes the client before re-failing (catchCause → close → failCause); interrupts propagate as interrupts, never converted to failed status. `catalog.paginate` walks nextCursor with a duplicate-cursor Set guard (throws on a repeated cursor) and a 1000-page cap; `listTools` falls back to `TolerantListToolsResultSchema` (outputSchema omitted) when SDK validation fails on broken $ref outputSchema references (regex match on the error message).

**Invariant:** A failed connect never leaks a transport (release closes on failure exit only); an auth-classified failure stops the fallback ladder (a 401 from StreamableHTTP is not retried over SSE); a post-connect defect always closes the client before surfacing; a repeated list cursor is a hard error, not an infinite loop.
**Probe:** `packages/opencode/test/server/httpapi-mcp.test.ts` ("serves status endpoint" pins `{demo:{status:"disabled"}}` for an enabled:false local config; "serves add, connect, and disconnect endpoints" pins add→disabled status map, disconnect→true, connect→true, disconnect→true against echo commands). Source pin:
```bash
grep -n 'BUN_BE_BUN' packages/opencode/src/mcp/index.ts                      # expect 1
grep -n 'Exit.isFailure(exit)' packages/opencode/src/mcp/index.ts            # expect 1
grep -n 'MAX_LIST_PAGES' packages/opencode/src/mcp/catalog.ts                # expect 3
grep -n 'TolerantListToolsResultSchema' packages/opencode/src/mcp/catalog.ts # expect 2
```

## Liveness watch + descendant-process teardown
**Path/Symbol:** `packages/opencode/src/mcp/index.ts` (`watch` :442-471, `descendants` :418-438, dispose finalizer :531-556, `storeClient` :571-588).
**Signature:** `watch(s: State, name, client, bridge, timeout?) → void`; `descendants(pid) → Effect<number[]>` (scoped, catch-all → []).
**Data Shape:** State = `{config, status, clients, defs, instructions}` records keyed by server name; ToolsChanged event `{server: name}` published on close and on tool-list change.

### Decisive source
```ts
// mcp/index.ts:443-449 — stale-closure guard: only the CURRENT client may mutate state
client.onclose = () => {
  if (s.clients[name] !== client) return
  delete s.clients[name]; delete s.defs[name]; delete s.instructions[name]
  s.status[name] = { status: "failed", error: "Connection closed" }
  bridge.fork(Effect.logWarning("MCP connection closed", { server: name }).pipe(
    Effect.andThen(events.publish(ToolsChanged, { server: name })), Effect.ignore))
}
// mcp/index.ts:462-470 — re-check BOTH guards after the async re-list
client.setNotificationHandler(ToolListChangedNotificationSchema, async () => {
  if (s.clients[name] !== client || s.status[name]?.status !== "connected") return
  const listed = await bridge.promise(McpCatalog.defs(client, timeout))
  if (!listed) return
  if (s.clients[name] !== client || s.status[name]?.status !== "connected") return
  s.defs[name] = listed
  await bridge.promise(events.publish(ToolsChanged, { server: name }).pipe(Effect.ignore))
})
// mcp/index.ts:538-548 — finalizer kills the whole process tree BEFORE closing the client
const pid = client.transport instanceof StdioClientTransport ? client.transport.pid : null
if (typeof pid === "number") {
  const pids = yield* descendants(pid)   // pgrep -P BFS; win32 → []
  for (const dpid of pids) { try { process.kill(dpid, "SIGTERM") } catch {} }
}
yield* Effect.tryPromise(() => client.close()).pipe(Effect.ignore)
```

**Flow:** `storeClient` installs the new client's watchers first, then closes the previous client. `watch()` wires onclose (state deletion + failed status + ToolsChanged) and ToolListChanged (re-list through the bridge, double-guarded before AND after the async list, then publish). The instance-state finalizer iterates all clients, SIGTERMs every stdio descendant found by pgrep -P BFS, then closes each client, then clears pendingOAuthTransports. The HTTP surface (groups/mcp.ts + handlers/mcp.ts, 8 endpoints under /mcp with the standard three-middleware stack) maps engine NotFoundError to typed McpServerNotFoundError (404), raises UnsupportedOAuthError (400) for local/disabled-oauth servers on auth/authenticate, decodes the add() result through the StatusMap schema (400 on decode failure), and checks authRemove membership via status() rather than config so runtime-added servers are removable.

**Invariant:** A replaced or disconnected client can never mutate registry state (identity check `s.clients[name] === client`); a re-list result arriving after disconnect/replacement is discarded; teardown kills grandchildren before closing the direct child so the SDK's own close cannot orphan them.
**Probe:** `packages/opencode/test/server/httpapi-mcp.test.ts` ("returns typed not found errors for missing MCP servers" pins exact 404 body `{_tag:"McpServerNotFoundError", name:"missing", message:"MCP server not found: missing"}` across all six /mcp/:name routes; "serves deterministic OAuth endpoints" pins 400 for auth/authenticate on a local server and DELETE auth → `{success:true}`). Source pin:
```bash
grep -n 'if (s.clients\[name\] !== client) return' packages/opencode/src/mcp/index.ts  # expect 1
grep -n 'pgrep' packages/opencode/src/mcp/index.ts                                        # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "MCP connectRemote connectLocal connectTransport watch descendants pendingOAuthTransports", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the acquireUseRelease ownership-transfer pattern for any connect-with-fallback ladder: the release step closes resources only on failure exit, so success hands ownership to the caller. Adopt auth-error classification as distinct statuses (not generic failure) with a break-out of the fallback ladder — retrying another transport after a 401 wastes time and confuses users. Adopt identity-guarded liveness handlers (the closure captures the client object; every mutation checks it is still current) — the standard fix for stale-closure races in long-lived registries. Adopt pgrep-BFS descendant kill before child close for stdio-spawned services. Adopt the tolerant-schema fallback for third-party list responses that violate your own validation (re-issue with a relaxed schema rather than failing the whole server). Adapt the five-state status union to your own auth model; omit the BUN_BE_BUN self-spawn env quirk and the TUI toast publication (replace with your own notification channel). Direct tests read whole (httpapi-mcp.test.ts 223L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
