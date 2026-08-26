<!-- capsule-v2 -->
# MCP bridge transports — stdio/SSE/ACP, IntelliJ SSE-preference ladder, bounded discovery

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the bridge connect client-provided MCP servers across three transports (stdio, SSE, ACP), prefer IntelliJ's in-process SSE endpoint, and build an immutable per-session tool catalog?

## MCP bridge transports
**Path/Symbol:** `src/acp/mcp-bridge.ts:AcpMcpBridge` (122-782) + `src/acp/mcp-sse.ts:SseMcpClient` + `src/acp/mcp-stdio.ts:StdioMcpClient`.
**Signature:** `AcpMcpBridge.start(): Promise<BridgeSpawnSettings>`; `#discoverTools(serverName, requestPage)`; `#initializeAndDiscover(...)`; `#callTool(id, exposedName, args)`.
**Data Shape:** `BridgeTool = { exposedName, connectionId, remoteName, description?, inputSchema, schemaHash? }`. Exposed names are `ide_<slug(server)>_<slug(tool)>`, with a `_<sha1 8>` suffix on collision. Defaults: discovery timeout 10s, runtime timeout 120s, max 32 pages, max 512 tools.

### Decisive source
```ts
// IntelliJ SSE preference: the launcher forwards to the IDE and exits 0, so prefer SSE
const ssePort = intellijSsePort(server)   // IJ_MCP_SERVER_PORT env
if (ssePort !== undefined) {
  attempts.push({ transport: 'sse', run: () => runSse(ssePort, true) })
  attempts.push({ transport: 'stdio', run: runStdio })   // stdio is the fallback
} else {
  attempts.push({ transport: 'stdio', run: runStdio })
}
for (const attempt of attempts) {
  try { remoteTools = await attempt.run(); break }
  catch (err) { /* close the failed client, record diagnostic, try next */ }
}
```
```ts
// bounded, cursor-paginated discovery
for (let page = 0; page < this.#maxPages; page++) {
  if (cursor !== undefined) {
    if (seenCursors.has(cursor)) { this.#catalogComplete = false; return tools }  // repeated cursor
    seenCursors.add(cursor)
  }
  const raw = await this.#withTimeout(paramsLabel, requestPage(cursor), this.#discoveryTimeoutMs)
  // validate tools array; dedupe by name; cap at #maxTools
  const nextCursor = result.nextCursor
  if (nextCursor === undefined || nextCursor === null || nextCursor === '') return tools
  cursor = nextCursor
}
this.#catalogComplete = false   // hit page cap
```

**Flow:** `start` creates the IPC server, filters supported servers (acp/stdio/command-shaped), and for each: ACP servers connect via `mcp/connect` + `mcp/message` initialize/tools-list; stdio servers spawn a child or, when the descriptor carries `IJ_MCP_SERVER_PORT`, prefer the IDE's in-process SSE endpoint (falling back to stdio). Each transport runs initialize → initialized → bounded cursor-paginated `tools/list`. Tools are deduped and exposed as `ide_*` names. The immutable catalog (tools + projectPath + catalogId/hash + complete flag) is set on the IPC server before the pi child spawns.

**Invariant:** Discovery is bounded (page cap, tool cap, repeated-cursor detection, per-RPC timeout) and sets `catalogComplete=false` on any truncation; the catalog is immutable for the session (changing IntelliJ MCP settings requires a new chat); runtime calls use a separate (longer) deadline from discovery; the SSE endpoint must stay on loopback (off-loopback endpoint events are rejected).

**Probe:** `test/unit/mcp-bridge.test.ts` ("AcpMcpBridge" describe block) and `test/unit/mcp-sse.test.ts` ("SseMcpClient" — connect/auth/HTTP 401 phase errors).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "AcpMcpBridge discoverTools intellijSsePort start", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-transport bridge, the IntelliJ SSE-preference ladder, bounded cursor-paginated discovery, and the immutable per-session catalog. Adapt the IntelliJ-specific descriptor keys (`IJ_MCP_SERVER_PORT`/`IJ_MCP_AUTH_TOKEN`) and the `ide_` naming scheme to the host. Omit the ACP-transport `mcp/connect`/`mcp/message` draft protocol unless the target client supports it.
