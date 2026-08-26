<!-- capsule-v2 -->
# refCount hub lifecycle — how do you dispose a shared MCP hub exactly when the last consumer leaves, without killing it mid-task?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How is hub teardown tied to client registration count, and what does disposal drain in which order?

## registerClient/unregisterClient bracket; dispose is idempotent and drains timers→watchers→connections
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`registerClient` :188–191; `unregisterClient` :197–206; `dispose` :1949–1995; WeakRef provider :151/:167).
**Signature:** `public async unregisterClient(): Promise<void>` — fires `dispose()` when `refCount <= 0`.
**Data Shape:** `refCount: number` per hub; `providerRef: WeakRef<ClineProvider>` so the hub never pins the panel it serves (deref-checked at every use: notify :1408, paths :478–485).

### Decisive source
```ts
// :202-205
if (this.refCount <= 0) {
    console.log("McpHub: Last client unregistered. Disposing hub.")
    await this.dispose()
}
```
```ts
// :1949-1955 + drain order — idempotence latch first, then timers → watchers → connections → disposables
if (this.isDisposed) { return }
this.isDisposed = true
for (const timer of this.configChangeDebounceTimers.values()) { clearTimeout(timer) }
...
this.removeAllFileWatchers()
for (const connection of this.connections) {
    try { await this.deleteConnection(connection.server.name, connection.server.source) } catch ...
}
```

**Flow:** each webview/provider registers on adopt and unregisters on dispose; zero-crossing triggers full drain: debounce timers cleared → flagResetTimer cleared → programmatic flag reset → per-server file watchers closed → every connection deleted via the NORMAL deleteConnection path (transport.close then client.close inside try/catch so one stuck server cannot abort the rest) → connections emptied → settings/project watchers disposed → vscode disposables released.
**Invariant:** dispose must be re-entrant safe (`isDisposed` checked before ANY side effect) because unregister can race panel teardown; connection teardown reuses deleteConnection rather than raw closes so sanitized-name registry entries and file watchers are cleaned by the same code path as user-initiated deletes.
**Probe:** describe-level coverage: `"Null safety improvements"` it `"should handle connection deletion safely"` (:712–768) exercises deleteConnection error tolerance; dispose itself is exercised transitively via ClineProvider lifecycle specs. Deterministic probe:
`grep -c 'isDisposed' src/services/mcp/McpHub.ts` = **3** (:156 field, :1951 check, :1955 set), `grep -c 'WeakRef' src/services/mcp/McpHub.ts` = **2** (:151 type, :167 construction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "McpHub dispose refCount unregisterClient", limit: 5 });
// Class cluster row Roo-Code.src.services.mcp.McpHub.McpHub resolves rank#1 for McpHub queries (verified via connectToServer/validateServerConfig families)
```

## Verdict
Adopt refcount-bracketed disposal with the fixed drain order and idempotence latch. Adapt the WeakRef pattern to your host's panel lifecycle. Omit nothing.
