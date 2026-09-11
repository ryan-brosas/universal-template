<!-- capsule-v2 -->
# Memoized connect lifecycle — how does a multi-server MCP host connect to one server exactly once and return a uniform connected/failed/needs-auth result?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do I connect to a single MCP server across 8 transport types and get back one discriminated result without ever double-connecting?

## Transport dispatch inside one memoized function
**Path/Symbol:** `src/services/mcp/client.ts`:`connectToServer` (:595-1641), key fn `getServerCacheKey` (:581-586).
**Signature:** `connectToServer(name: string, serverRef: ScopedMcpServerConfig, serverStats?): Promise<MCPServerConnection>` wrapped in lodash `memoize(fn, getServerCacheKey)` where cacheKey = `` `${name}-${jsonStringify(serverRef)}` ``.
**Data Shape:** Returns `MCPServerConnection = {type:'connected', name, client, capabilities, serverInfo, instructions, config, cleanup} | {type:'failed', name, config, error} | {type:'needs-auth', name, config} | {type:'disabled', name, config}` — callers never see thrown connect errors for remote types; failures become `failed` results (:1632-1637).

### Decisive source
```ts
export const connectToServer = memoize(
  async (name, serverRef, serverStats): Promise<MCPServerConnection> => {
    // transport selection by serverRef.type:
    // 'sse'  → SSEClientTransport + ClaudeAuthProvider + wrapFetchWithTimeout(wrapFetchWithStepUpDetection(createFetchWithInit()))
    //          eventSourceInit.fetch MUST NOT carry the timeout wrapper (:643-671)
    // 'http' → StreamableHTTPClientTransport; ingress Authorization header only when !hasOAuthTokens (:812,:833-836)
    // 'ws'   → WebSocketTransport over Bun globalThis.WebSocket or ws pkg cast to WsClientLike (:735-783)
    // 'sse-ide'/'ws-ide' → no-auth IDE variants; X-Claude-Code-Ide-Authorization for ws-ide (:708-734)
    // 'claudeai-proxy' → StreamableHTTP to `${MCP_PROXY_URL}${MCP_PROXY_PATH.replace('{server_id}', id)}` (:868-904)
    // 'sdk'  → throw new Error('SDK servers should be handled in print.ts') (:867)
    // stdio/undefined → StdioClientTransport({command,args,env:{...subprocessEnv(),...cfg.env}, stderr:'pipe'});
    //   CLAUDE_CODE_SHELL_PREFIX rewrites to shell -c "<cmd args joined>" (:944-958)
    // Chrome/ComputerUse stdio servers run IN-PROCESS via createLinkedTransportPair() to avoid a ~325MB subprocess (:905-943)
```

**Flow:** build transport → attach stderr accumulator (stdio only, capped at 64MB :971-982) → create SDK `Client` with capabilities `{roots:{}, elicitation:{}}` (:985-1002; empty object REQUIRED — sending `{form:{},url:{}}` breaks Java/Spring AI servers whose Elicitation class has zero fields :996-999) → register ListRoots handler returning `file://${getOriginalCwd()}` (:1009-1018) → `Promise.race([client.connect(transport), timeout])` with `getConnectionTimeoutMs()` = env `MCP_TIMEOUT` or 30000ms; on timeout close transport AND inProcessServer before rejecting (:1048-1077) → truncate instructions >2048 chars (:1160-1171) → install default elicitation handler that returns `{action:'cancel'}` until UI registration overwrites it (:1191-1197) → install error/close bridge handlers (see mcp-reconnect-onclose-bridge) → register process-exit `cleanup` (SIGINT→SIGTERM→SIGKILL escalation for stdio children, total ≤600ms :1429-1562) → return `connected` with wrappedCleanup.
**Invariant:** The memoize key includes the FULL serialized config, so editing any field (url/env/command) produces a different key = fresh connection; every early-return path (timeout, UnauthorizedError→needs-auth, throw) must still `transport.close()` + close inProcessServer or child processes leak.
**Probe:** `grep -n 'export const connectToServer = memoize(' src/services/mcp/client.ts | head -1` (`595:` — single memoized entry point).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getRemoteMcpServerConnectionBatchSize", limit: 5 });
// ranks connectToServer's batch-size siblings; then trace_path outbound from
// locoagent.src.services.mcp.client.connectToServer for the full callee set
```

## Verdict
Adopt memoize-by-full-config + three-state result union + capability-declaration minimalism (`elicitation: {}`). Adapt transport matrix to your host's supported types (drop claudeai-proxy/sdk/IDE twins). Omit product telemetry events and feature-flagged in-process servers unless you have their native modules.
