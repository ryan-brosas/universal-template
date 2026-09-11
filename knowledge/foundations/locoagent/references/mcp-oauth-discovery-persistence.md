<!-- capsule-v2 -->
# Discovery-state persistence budget — why does storing full OAuth metadata corrupt the macOS keychain, and what exactly should be persisted?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Which discovery fields survive restarts, and what size constraint forces the split?

## URLs yes, metadata blobs no — the SDK re-fetches the rest
**Path/Symbol:** `src/services/mcp/auth.ts`: `saveDiscoveryState` (:1997-2035), `discoveryState()` reader (:2037-2088), config-hint branch via fetchAuthServerMetadata (:2059-2085).
**Signature:** persists ONLY `{authorizationServerUrl, resourceMetadataUrl}` alongside stub `accessToken:''`/`expiresAt:0` placeholders that keep the entry structurally valid.
**Data Shape:** authorizationServerMetadata alone ≈1.5–2KB per server (every grant type/PKCE method/endpoint); keychain write goes through `security -i` with a 4096-byte stdin line limit → ~2013 bytes of hex-encoded JSON total.

### Decisive source
```ts
// Persist only the URLs, NOT the full metadata blobs.
// authorizationServerMetadata alone is ~1.5-2KB per MCP server ... On macOS the
// keychain write goes through `security -i` which has a 4096-byte stdin
// line limit — with hex encoding that's ~2013 bytes of JSON total. Two
// OAuth MCP servers persisting full metadata overflows it, corrupting
// the credential store (#30337). The SDK re-fetches missing metadata
// with one HTTP GET on the next auth — see node_modules/.../auth.js
// `cachedState.authorizationServerMetadata ?? await discover...`
const updatedData: SecureStorageData = { ...existingData,
  mcpOAuth: { ...existingData.mcpOAuth,
    [serverKey]: { ...existingData.mcpOAuth?.[serverKey],
      serverName: this.serverName, serverUrl: this.serverConfig.url,
      accessToken: existingData.mcpOAuth?.[serverKey]?.accessToken || '',
      expiresAt: existingData.mcpOAuth?.[serverKey]?.expiresAt || 0,
      discoveryState: {
        authorizationServerUrl: state.authorizationServerUrl,
        resourceMetadataUrl: state.resourceMetadataUrl,
      },
    },
  },
}
```

**Flow:** SDK completes discovery during connect/auth → saveDiscoveryState stores just the two URLs → next session's `_doRefresh` uses the persisted AS URL to re-discover metadata in one GET instead of the RFC 9728→8414 chain (:2230-2240); the reader ALSO honors an explicit `oauth.authServerMetadataUrl` config hint before giving up undefined.
**Invariant:** Never persist provider metadata blobs into size-limited secure storage — two servers suffice to brick the store for ALL credentials; placeholder accessToken/expiresAt keep entries present so hasMcpDiscoveryButNoToken-style logic can distinguish probed-no-token from never-seen.
**Probe:** `grep -n '4096-byte stdin' src/services/mcp/auth.ts` (`2010:`) and `grep -n 'authorizationServerUrl: state.authorizationServerUrl,' src/services/mcp/auth.ts` (`2027:`) and `grep -n \"cached.authorizationServerMetadata as OAuthDiscoveryState\" src/services/mcp/auth.ts` (`2055:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "saveDiscoveryState", limit: 5 });
```

## Verdict
Adopt URL-only persistence + placeholder-shaped entries + one-GET re-discovery on refresh. Adapt your secure-storage constraints (if unlimited, persisting blobs is merely wasteful, not corrupting).
