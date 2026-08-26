<!-- capsule-v2 -->
# Reconnect-onclose bridge — how do I detect a dead MCP connection when the SDK fires onerror but never onclose?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do pending callTool promises get rejected after a transport dies, so the next call reconnects instead of hanging forever?

## Terminal-error counting closes what the SDK leaves open
**Path/Symbol:** `src/services/mcp/client.ts`: onerror override (:1266-1371), `closeTransportAndRejectPending` (:1240-1247), onclose override (:1374-1402), consts `MAX_ERRORS_BEFORE_RECONNECT = 3` (:1228), `isTerminalConnectionError` (:1249-1263).
**Signature:** installed per-connection inside connectToServer: saves `originalOnerror/originalOnclose`, wraps both, tracks `consecutiveConnectionErrors` and re-entry guard `hasTriggeredClose`.
**Data Shape:** terminal-error message substrings: ECONNRESET / ETIMEDOUT / EPIPE / EHOSTUNREACH / ECONNREFUSED / "Body Timeout Error" / "terminated" / "SSE stream disconnected" / "Failed to reconnect SSE stream" / "Maximum reconnection attempts".

### Decisive source
```ts
// comment verbatim :1234-1239:
// client.close() → transport.close() → transport.onclose → SDK's _onclose():
// rejects all pending request handlers (so hung callTool() promises fail with
// McpError -32000 "Connection closed") and then invokes our client.onclose
// handler below (which clears the memo cache so the next call reconnects).
const closeTransportAndRejectPending = (reason: string) => {
  if (hasTriggeredClose) return          // close() aborts in-flight streams which
  hasTriggeredClose = true               // may fire onerror again before close chain completes
  void client.close().catch(e => { /* logged */ })
}
// onerror: session-expired (404 + JSON-RPC -32001) closes IMMEDIATELY (:1313-1329);
// "Maximum reconnection attempts" (SDK exhausted its own SSE retries) closes IMMEDIATELY (:1338-1348);
// otherwise terminal errors count up to 3 then close; NON-terminal errors reset the counter to 0 (:1361-1364).
// onclose: deletes fetch caches by NAME + connectToServer.cache by KEY (:1383-1397).
```

**Flow:** transport error → onerror classifies → either immediate close (session-expired, SSE-reconnection-exhausted) or 3rd consecutive terminal error → closeTransportAndRejectPending → SDK rejects all pending request handlers → our onclose runs → clears `fetchToolsForClient/fetchResourcesForClient/fetchCommandsForClient` caches keyed by server NAME plus `connectToServer.cache` keyed by name+config → next ensureConnectedClient misses cache and reconnects fresh.
**Invariant:** Calling only `client.onclose?.()` manually would clear caches but LEAVE pending tool calls hung — you must go through `client.close()` so the SDK's `_onclose` rejects in-flight handlers first. Non-terminal errors must RESET the counter or one transient blip plus two old ones force-kills healthy connections.
**Probe:** `grep -n 'MAX_ERRORS_BEFORE_RECONNECT = 3' src/services/mcp/client.ts` (`1228:`) and `grep -n "fetchToolsForClient.cache.delete(name)" src/services/mcp/client.ts` (`1389:` — name-keyed fetch-cache clearing lives in the onclose path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "closeTransportAndRejectPending", limit: 5 });
// resolves the closure + terminal-classification block line-exact
```

## Verdict
Adopt the error-counting close bridge, the immediate-close triggers, and delete-on-close of BOTH name-keyed and key-keyed caches. Adapt the terminal-substring list to your transports' real error vocabulary. Omit per-transport debug logging taxonomy.
