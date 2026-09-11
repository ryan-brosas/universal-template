<!-- capsule-v2 -->
# Stdio stderr capture via start-then-monkey-patch — how do you intercept a transport's stderr stream when the SDK only exposes it AFTER start(), but connect() both starts the transport and consumes the stream?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does the hub capture stdio server stderr from the very first connection byte, given that `transport.stderr` exists only after `start()` while `client.connect(transport)` is what starts it?

## Start yourself, patch start to a no-op, then connect
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`connectToServer` stdio arm :706–780; the no-op override :856–858; `client.connect(transport)` :878).
**Signature:** `transport = new StdioClientTransport({ command, args, cwd, env: {...getDefaultEnvironment(), ...(configInjected.env || {})}, stderr: "pipe" })`.
**Data Shape:** `stderr: "pipe"` forces the SDK to pipe child stderr instead of inheriting. After `await transport.start()`, `transport.stderr` is a readable stream; handlers are attached BEFORE `.connect()`. Env is SDK default environment SPREAD UNDER user env (user wins).

### Decisive source
```ts
// :753-755 — the comment IS the design rationale
// As a workaround, we start the transport ourselves, and then monkey-patch the start method
// to no-op so that .connect() doesn't try to start it again.
await transport.start()
const stderrStream = transport.stderr
```
```ts
// :761-776 — INFO lines vs error lines split on a regex, not on stream identity
const isInfoLog = /INFO/i.test(output)
if (isInfoLog) {
    console.log(`Server "${name}" info:`, output)
} else {
    console.error(`Server "${name}" stderr:`, output)
    const connection = this.findConnection(name, source)
    if (connection) {
        this.appendErrorMessage(connection, output)
        if (connection.server.status === "disconnected") {
            await this.notifyWebviewOfServerChanges()
        }
    }
}
```
```ts
// :855-858 — override applied ONLY for stdio transports that were already started
if (configInjected.type === "stdio") {
    transport.start = async () => {}
}
```

**Flow:** build transport with piped stderr → attach `onerror`/`onclose` status-flip handlers → `await transport.start()` → attach stderr data handler (INFO-regex triage → appendErrorMessage + webview notify only when already disconnected) → monkey-patch `start` to no-op → push connection with `status: "connecting"` → `await client.connect(transport)` (starts nothing; speaks protocol over the live pipes) → flip to `"connected"`, clear error, read `client.getInstructions()`, fetch tools/resources/templates.
**Invariant:** the stderr handler MUST be attached before any protocol traffic — connection-phase crash output is exactly what this exists to capture; and `start` must be neutered ONLY for stdio (the url transports own their own lifecycle). Any port that calls `.connect()` directly loses pre-connect stderr forever.
**Probe:** `src/services/mcp/__tests__/McpHub.spec.ts` describe `"Windows command wrapping"` → it `"should handle case-insensitive cmd command check"` (:2309–2366) drives `initializeGlobalMcpServers` through real `StdioClientTransport` mocks asserting the constructed config (`command: "CMD"`, args unwrapped) and the post-connect flow.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "connectToServer stdio transport start monkey-patch", limit: 5 });
// CLI verified @ pin: rank#1 line-exact → McpHub.connectToServer Method src/services/mcp/McpHub.ts 655-896 (total: 70)
```

## Verdict
Adopt the start→patch→connect sequencing verbatim — it is the only ordering that captures pre-connection stderr. Adapt the `/INFO/i` heuristic to your servers' log dialects. Omit the Windows cmd.exe wrapping decision living in the same arm (own capsule).
