<!-- capsule-v2 -->
# Session-expiry recovery ladder — how does a tool call survive a server-side MCP session loss (404 + JSON-RPC -32001) without surfacing an error to the model?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do I detect session expiry across two different error shapes and retry exactly once on a fresh connection?

## Two error shapes, one cache-clearing retry
**Path/Symbol:** `src/services/mcp/client.ts`: classifier `isMcpSessionExpiredError` (:193-206); catch-side detection incl. derived -32000 "Connection closed" (:3210-3231); retry loop in MCPTool.call (:1859-1922, `MAX_SESSION_RETRIES = 1` :1859); `McpSessionExpiredError` class (:165-170).
**Signature:** `isMcpSessionExpiredError(error: Error): boolean`; inner `callMCPTool` throws `McpSessionExpiredError` after `clearServerCache(name, config)`; the outer per-call loop catches it and retries with a fresh client.
**Data Shape:** Shape 1 = StreamableHTTPError `{code:404}` whose message embeds `{"error":{"code":-32001,"message":"Session not found"}}` (both spacings checked). Shape 2 = McpError `{code:-32000}` message containing "Connection closed" — what the pending callTool actually rejects with after closeTransportAndRejectPending, gated to http/claudeai-proxy configs.

### Decisive source
```ts
export function isMcpSessionExpiredError(error: Error): boolean {
  const httpStatus = 'code' in error ? (error as Error & { code?: number }).code : undefined
  if (httpStatus !== 404) return false
  // The SDK embeds the response body text in the error message.
  // We check for the JSON-RPC error code to distinguish from generic web server 404s.
  return (
    error.message.includes('"code":-32001') ||
    error.message.includes('"code": -32001')
  )
}
...
if (isSessionExpired || isConnectionClosedOnHttp) {
  await clearServerCache(name, config)   // drops connection + all fetch caches
  throw new McpSessionExpiredError(name) // outer loop: attempt < MAX_SESSION_RETRIES → continue
}
```

**Flow:** callTool → 404/-32001 arrives directly OR surfaces as -32000 Connection-closed after the onerror bridge closed the transport → classify → clearServerCache (memoized connect + fetch caches dropped) → throw typed sentinel → MCPTool.call's `for (attempt…)` loop sees `McpSessionExpiredError` under budget → `continue` → ensureConnectedClient creates a brand-new session → second failure propagates to the model. URL elicitations ride the SAME loop via `callMCPToolWithUrlElicitationRetry` (`MAX_URL_ELICITATION_RETRIES = 3` :2850; SDK creates plain McpError so detection is by `error.code !== ErrorCode.UrlElicitationRequired` :2864-2869 — NOT instanceof).
**Invariant:** Retry only AFTER clearing caches — retrying through the memoized dead connection just replays the expired session ID. Check BOTH error shapes or HTTP-transport expiry hangs pending calls as -32000 while you wait for a 404 that already became a transport close.
**Probe:** `grep -n 'MAX_SESSION_RETRIES = 1' src/services/mcp/client.ts` (`1859:`) and `grep -n 'MAX_URL_ELICITATION_RETRIES = 3' src/services/mcp/client.ts` (`2850:`) and `grep -n 'error.code !== ErrorCode.UrlElicitationRequired' src/services/mcp/client.ts` (`2866:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "callMCPToolWithUrlElicitationRetry", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isMcpSessionExpiredError", limit: 5 });
```

## Verdict
Adopt dual-shape expiry classification + clear-cache-then-retry-once + error-code (not instanceof) elicitation detection. Adapt retry budgets. Omit REPL queue/URL-dialog plumbing (elicitationHandler queue capsule covers it).
