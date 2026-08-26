<!-- capsule-v2 -->
# MCP bridge IPC — authenticated per-session socket, catalog handshake + registration validation

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter expose remote MCP tools to the pi subprocess over an authenticated local IPC channel, and how does it validate the pi extension's registration acknowledgement?

## MCP bridge IPC
**Path/Symbol:** `src/acp/mcp-ipc.ts:McpIpcServer` (72-342) + `src/acp/mcp-types.ts` (`BRIDGE_IPC_VERSION`, `BridgeIpcMessage`, `CatalogRegistration`).
**Signature:** `static McpIpcServer.start(sessionId): Promise<McpIpcServer>`; `setCatalog(catalog)`; `waitForHandshake()`; `waitForRegistration(timeoutMs)`; `send(msg)`; `close()`.
**Data Shape:** Unix domain socket (or Windows named pipe) in a private temp dir; a 24-byte hex `token`; single-client (only the first authenticated connection is accepted). Messages are NDJSON with a 1 MiB frame cap. `BridgeCatalog = { tools, projectPath?, catalogId?, catalogHash?, complete?, diagnostics? }`.

### Decisive source
```ts
// hello: authenticate once
if (msg.token !== this.#token || msg.sessionId !== this.#sessionId) {
  this.send({ type:'error', id:'', code:'unauthorized', message:'Invalid token or session id' }); this.#client?.destroy(); return
}
if (msg.version !== BRIDGE_IPC_VERSION) { /* version_mismatch, destroy */ }
this.#authenticated = true
this.#handshakeCatalog = this.#catalog
this.send({ type:'hello_ack', catalog: this.#catalog })   // catalog set BEFORE spawn
this.#handshakeResolve?.(this.#catalog)
```
```ts
// catalog_registered: validate completeness + schema hashes
const expected = new Map(catalog.tools.map(t => [t.exposedName, t]))
for (const [kind, entries] of [['registered', r.registered], ['failed', r.failed]]) {
  for (const e of entries) {
    if (!expected.has(e.exposedName)) return 'unknown tool'
    if (seen.has(e.exposedName)) return 'duplicate tool'
    if (expectedHash !== undefined && e.schemaHash !== expectedHash) return 'schema hash mismatch'
  }
}
const missing = [...expected.keys()].filter(name => !seen.has(name))
return missing.length ? `omitted tools: ${missing.join(', ')}` : undefined
```

**Flow:** `start` creates the socket + token, arms a 20s handshake timeout, and returns an endpoint. The catalog is set before the pi child spawns, so the handshake `hello_ack` always carries the complete catalog. The pi extension connects, sends `hello` (version+token+sessionId); on success the server replies `hello_ack` and resolves the handshake. The extension then registers each tool and sends `catalog_registered`; the server validates every entry (known name, no dupes, schema-hash match, no omissions) and rejects with `catalog_mismatch` on any problem. On client close before registration, pending registration waiters reject.

**Invariant:** The catalog is immutable and set before spawn; only the first authenticated client is accepted; the registration acknowledgement must cover every catalog tool with matching schema hashes (partial/duplicate/unknown → reject); the socket file is `chmod 0600` on POSIX and cleaned up on close.

**Probe:** `test/unit/mcp-bridge.test.ts` ("McpIpcServer handshake" describe block) — pins the hello/auth/registration validation contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "McpIpcServer validateCatalogRegistration hello_ack", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the token-authenticated single-client IPC server, catalog-before-spawn, and the strict registration validation (completeness + schema-hash). Adapt the socket path, token generation, and the frame cap to the host. Omit the Windows named-pipe branch unless the target runs on Windows.
