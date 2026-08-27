<!-- capsule-v2 -->
# MCP protocol-era discovery — how does one client serve 2025-11-25 and 2026-07-28 servers?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** The 2026 spec replaced the `initialize` handshake with stateless requests carrying metadata — how does the client pick an era without breaking legacy servers?

## Probe-first era negotiation
**Path/Symbol:** `packages/mcp/src/tool/mcp-client.ts` — `protocolEra` field (:432), discovery attempt (:544–556), `tryProtocolDiscovery` (:609–639), error-code constants (:82), version constants `types.ts:5–6`.
**Signature:** `tryProtocolDiscovery(signal?) => Promise<boolean>`; `MODERN_PROTOCOL_ERROR_CODES = [-32020, -32021, -32022]`; `LATEST_PROTOCOL_VERSION='2026-07-28'`, `LATEST_LEGACY_PROTOCOL_VERSION='2025-11-25'`.
**Data Shape:** `DiscoverResultSchema` result carries `supportedVersions` (validated against the client's requested version before adoption).

### Decisive source
```ts
if (this.transport.supportsProtocolVersionDiscovery) {
  const discovered = await this.tryProtocolDiscovery(signal);
  if (discovered) return this;
}
this.protocolEra = 'legacy';
this.protocolVersion = LATEST_LEGACY_PROTOCOL_VERSION;
...
private async tryProtocolDiscovery(signal): Promise<boolean> {
  this.protocolEra = 'modern';
  this.protocolVersion = LATEST_PROTOCOL_VERSION;
  try {
    const result = await this.request({ request: {method: 'server/discover'},
      resultSchema: DiscoverResultSchema,
      options: { signal, timeout: DEFAULT_PROTOCOL_DISCOVERY_TIMEOUT /*1000ms*/ } });
    this.applyDiscoverResult(result);   // throws if requested version unsupported
    return true;
  } catch (error) {
    if (MCPClientError.isInstance(error) && error.code != null
        && MODERN_PROTOCOL_ERROR_CODES.includes(error.code))
      throw error;                       // modern server REJECTED us: fatal, not fallback
    return false;                        // legacy server: fall back to initialize
  }
}
```

**Flow:** connect → if transport advertises discovery support, optimistically set modern era and send `server/discover` under a 1s timeout → success validates supportedVersions and stays modern → a MODERN-protocol rejection code (-32020/-32021/-32022) is rethrown as fatal (server understood but refused) → any other failure (timeout, method-not-found on old servers) falls back to the full legacy `initialize` handshake at 2025-11-25.
**Invariant:** Era selection is optimistic-probe-then-fallback, and ONLY non-modern failures may trigger fallback — treating a modern server's typed rejection as "try legacy" would mask real incompatibilities. Transports declare participation via `supportsProtocolVersionDiscovery` so stdio can opt out.
**Probe:** deterministic probes: `grep -c "MODERN_PROTOCOL_ERROR_CODES.includes" packages/mcp/src/tool/mcp-client.ts` → `1`; `grep -cF "LATEST_LEGACY_PROTOCOL_VERSION = '2025-11-25'" packages/mcp/src/tool/types.ts` → `1`. Direct tests: `mcp-client.test.ts` discovery suites (#19026).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "tryProtocolDiscovery protocolEra", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 tryProtocolDiscovery :609-639
```

## Verdict
Adopt probe-first negotiation with fatal-vs-fallback error classification and the 1s discovery timeout; adapt the error-code table to your spec revision; omit nothing — naive version-string matching cannot distinguish "old server" from "modern server refusing you".
