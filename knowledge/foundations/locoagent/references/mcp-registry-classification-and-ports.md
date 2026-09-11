<!-- capsule-v2 -->
# Official-registry URL classification and OAuth redirect ports — how do I flag known-official MCP endpoints and pick a safe loopback callback port?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How is the official-server set fetched/matched, and why is the redirect port range platform-dependent with random selection?

## Fail-closed registry set + Windows range avoidance + random probe
**Path/Symbol:** `src/services/mcp/officialRegistry.ts` (whole :1-72): `prefetchOfficialMcpUrls` (5s axios timeout; skipped under CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC), normalization identical to `getLoggingSafeMcpBaseUrl` (strip query + trailing slash) "so direct Set.has() lookup works" (:15-17); `isOfficialMcpUrl` fail-closed (`officialUrls?.has(...) ?? false` :66-68). `src/services/mcp/oauthPort.ts`: REDIRECT_PORT_RANGE (:9-12), fallback 3118 (:13), `findAvailablePort` random probe capped at 100 attempts (:36-78).
**Signature:** `buildRedirectUri(port = REDIRECT_PORT_FALLBACK)` → `` `http://localhost:${port}/callback` `` — fixed path per RFC 8252 §7.3 loopback rule (any port, path must match).
**Data Shape:** Windows dynamic port range 49152-65535 RESERVED → range shifts to {min:39152, max:49151}; env MCP_OAUTH_CALLBACK_PORT overrides.

### Decisive source
```ts
// officialRegistry: undefined registry → false (fail-closed).
export function isOfficialMcpUrl(normalizedUrl: string): boolean {
  return officialUrls?.has(normalizedUrl) ?? false
}
// oauthPort: Uses random selection for better security
for (let attempt = 0; attempt < maxAttempts; attempt++) {
  const port = min + Math.floor(Math.random() * range)
  try { await test-listen(port); return port } catch { continue }
}
// If random selection failed, try the fallback port (3118), else throw 'No available ports'
```

**Flow:** startup prefetches the commercial registry (fire-and-forget) → UI/security surfaces classify server URLs by normalized membership. During an OAuth browser flow: configured port → random available port in the platform-safe range → fallback 3118 → hard error; performMCPOAuthFlow's EADDRINUSE handler then prints a platform-specific lsof/netstat diagnostic (auth.ts :1153-1169).
**Invariant:** Un-fetched registry must classify NOTHING as official (fail-closed); the URL normalizer used for logging and for registry matching MUST be the same function family or Set.has() silently misses; port selection avoids the OS ephemeral range on Windows to prevent hijack collisions.
**Probe:** `grep -n 'officialUrls?.has(normalizedUrl) ?? false' src/services/mcp/officialRegistry.ts` (`67:`) and `grep -n '{ min: 39152, max: 49151 }' src/services/mcp/oauthPort.ts` (`11:`) and `grep -n 'REDIRECT_PORT_FALLBACK = 3118' src/services/mcp/oauthPort.ts` (`13:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "prefetchOfficialMcpUrls", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "findAvailablePort", limit: 5 });
```

## Verdict
Adopt both small modules nearly verbatim (~150 lines). Adapt the registry endpoint. Keep the shared-normalization requirement and fail-closed default.
