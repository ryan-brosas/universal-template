<!-- capsule-v2 -->
# MCP streamable-HTTP era split — which sessions/SSE features survive in the 2026 transport?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What exactly must a transport gate behind `isModernProtocol()`, and how do auth/SSE behaviors differ per era?

## Era-gated transport behavior
**Path/Symbol:** `packages/mcp/src/tool/mcp-http-transport.ts` — capability flags (:40–41), `isModernProtocol` (:125–130), sessionId gating (:146), inbound SSE control (:114–118, :174–180, :240, :331), header mirroring (:285–286).
**Signature:** `supportsProtocolVersionDiscovery = true`, `supportsMcpToolParameterHeaders = true` (readonly class fields); `isModernProtocol(): boolean`.
**Data Shape:** `MCPTransportSendOptions` now carries `{signal?, headers?}` — per-request headers ride EVERY send in modern mode.

### Decisive source
```ts
private isModernProtocol(): boolean {
  return (this.protocolVersion ?? LATEST_PROTOCOL_VERSION) === LATEST_PROTOCOL_VERSION;
}
// session id: only legacy keeps Mcp-Session-Id semantics
if (!this.isModernProtocol() && includeSessionId && this.sessionId) { ... }
// inbound SSE: modern = stateless, no listening connection; legacy = required
if (this.isModernProtocol()) { this.inboundSseConnection?.close(); this.inboundSseConnection = undefined; return; }
if (!this.inboundSseConnection) { this.startInboundSse(); }
```

**Flow:** constructor defaults `initialProtocolVersion ?? LATEST_LEGACY_PROTOCOL_VERSION`; after discovery flips the era, reconnect logic CLOSES the inbound SSE in modern mode (stateless POSTs + optional per-request response streams) while legacy mode lazily STARTS it; modern sends merge caller headers (incl. `Mcp-Param-*` bindings) into every request; session-id headers are suppressed entirely.
**Invariant:** The era check is ONE method consulted at every behavioral fork — session id inclusion, SSE lifecycle, header mirroring. Defaulting an ABSENT protocolVersion to LATEST (not legacy) means unknown-version transports behave modern by default.
**Probe:** deterministic probe: `grep -cE "throw new UnauthorizedError\(\);|throw error;" packages/mcp/src/tool/mcp-sse-transport.ts` → `4`. Companion SSE-auth change (#19264): auth failures and POST-error paths now THROW through the connect promise instead of swallowing via `onerror`+return, so callers observe real errors (`UnauthorizedError` preserved).
**Retrieve:** verified live @9d9a73f — search_graph `isModernProtocol supportsProtocolVersionDiscovery mcp-http-transport` rank#1 `HttpMCPTransport.isModernProtocol :125-130`.

## Verdict
Adopt single-predicate era gating + capability flags + throwing auth propagation; adapt SSE lifecycle to your server's notification model; omit stdio-specific shims unless porting that transport too.
