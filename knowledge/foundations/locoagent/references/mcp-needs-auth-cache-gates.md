<!-- capsule-v2 -->
# Needs-auth cache and skip gates — how do I stop re-probing MCP servers that can't authenticate for at least 15 minutes?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Where do 401 results get cached, how are concurrent cache writes serialized, and when is a connection attempt skipped entirely?

## File-backed TTL cache + promise-chain write serialization + discovery-without-token gate
**Path/Symbol:** `src/services/mcp/client.ts`: `MCP_AUTH_CACHE_TTL_MS = 15*60*1000` (:257), memoized reader `getMcpAuthCache`/`isMcpAuthCached` (:269-287), serialized writer `setMcpAuthCacheEntry` (:291-309), `clearMcpAuthCache` (:311-316), `handleRemoteAuthFailure` (:340-361); consumer gate in `getMcpToolsCommandsAndResources.processServer` (:2307-2322); counterpart probe-skip `hasMcpDiscoveryButNoToken` (auth.ts :349-363).
**Signature:** `setMcpAuthCacheEntry(serverId: string): void` (sync, fire-and-forget via chain); gate: `(await isMcpAuthCached(name)) || ((type==='http'||type==='sse') && hasMcpDiscoveryButNoToken(name, config))`.
**Data Shape:** Cache file `<configHome>/mcp-needs-auth-cache.json`, `{[serverId]: {timestamp}}`; read path catches all errors to `{}`.

### Decisive source
```ts
// Serialize cache writes through a promise chain to prevent concurrent
// read-modify-write races when multiple servers return 401 in the same batch
let writeChain = Promise.resolve()
function setMcpAuthCacheEntry(serverId: string): void {
  writeChain = writeChain.then(async () => {
    const cache = await getMcpAuthCache()
    cache[serverId] = { timestamp: Date.now() }
    await mkdir(dirname(cachePath), { recursive: true })
    await writeFile(cachePath, jsonStringify(cache))
    authCachePromise = null   // invalidate the READ cache; safe because the next
  }).catch(() => {})          // write's getMcpAuthCache() re-reads WITH this entry present
}
// consumer (:2307-2322): claudeai-proxy/http/sse servers SKIP connectToServer,
// report type:'needs-auth', and still surface createMcpAuthTool(name, config) so
// the user has an inline authenticate action. The second check closes the gap the
// TTL leaves open: probed-before-but-no-token servers would otherwise be re-probed
// every 15 minutes with a guaranteed 401 + OAuth-discovery round trip.
```

**Flow:** remote transport connect fails with UnauthorizedError / 401 → `handleRemoteAuthFailure` emits analytics + writes cache entry through chain → returns needs-auth connection → batch processor short-circuits future attempts until TTL expires — UNLESS XAA is enabled and configured (`hasMcpDiscoveryButNoToken` returns false for xaa servers because cached id_token can silently re-auth), which keeps that auto-auth branch reachable.
**Invariant:** The read-cache invalidation inside the chained write is only race-free BECAUSE writes are serialized by `writeChain` — parallelizing the writes reintroduces last-writer-wins loss. The no-token skip must exempt XAA or you brick zero-interaction re-auth.
**Probe:** `grep -n 'let writeChain = Promise.resolve()' src/services/mcp/client.ts` (`291:`) and `grep -cn 'authCachePromise = null' src/services/mcp/client.ts` (`2`) and `grep -n 'hasMcpDiscoveryButNoToken(name, config)' src/services/mcp/client.ts` (`2313:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "setMcpAuthCacheEntry", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "handleRemoteAuthFailure", limit: 5 });
```

## Verdict
Adopt the TTL file cache, the single-chain write serialization, and the two-condition skip gate (TTL ∪ discovery-without-token). Adapt cache location/TTL. Omit analytics fields.
