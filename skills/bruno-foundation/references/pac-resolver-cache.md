<!-- capsule-v2 -->
# PAC resolver cache — sandboxed PAC scripts with TTL'd promise-cache and single-flight download

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you fetch, cache, and evaluate Proxy-Auto-Config scripts safely (sandboxed JS) without hammering the PAC server or blocking concurrent requests?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/utils/pac-resolver.ts:getPacResolver` (:73-126), `downloadPac` (:37-58), `clearPacCache` (:128).
**Signature:** `getPacResolver({pacSource, httpsAgentRequestFields?, opts?: {cacheTtlMs?, timeoutMs?}}) → Promise<PacWrapper>` where `PacWrapper.resolve(url) → Promise<string[]>`.
**Data Shape:** module `CACHE = Map<string, {wrapper: Promise<PacWrapper>, ts}>` — caches PROMISES not results (single-flight: N concurrent callers await one download); key = `url:<pacSource>` for file/http, plus `|ca:<sha256-16hex>|ru:<rejectUnauthorized>|mv:<minVersion>` for https sources; TTL default 5 min.

### Decisive source
```ts
const wrapperPromise: Promise<PacWrapper> = (async () => {
  const script = await downloadPac(pacSource, httpsAgentRequestFields, opts.timeoutMs ?? 5000);
  // pac-resolver v7 uses QuickJS WASM sandbox — not affected by CVE GHSA-9j49-mfvp-vmhm (<v5)
  const qjs = await getQuickJS();
  const resolverFn = createPacResolver(qjs, script, { sandbox: { myIpAddress: getLocalIpAddress } });
  return {
    resolve: async (url: string) => {
      ...
      const out = await resolverFn(url, host);
      if (!out || typeof out !== 'string') return [];
      return out.split(';').map((s) => s.trim()).filter(Boolean);
    }
  };
})();
CACHE.set(key, { wrapper: wrapperPromise, ts: now });
try { return await wrapperPromise; }
catch (err) { CACHE.delete(key); throw err; }
```

**Flow:** key by source (+TLS fingerprint for https) → fresh promise ⇒ set cache THEN await → failure deletes its own entry so a poisoned download doesn't stick for the whole TTL → resolve() splits the PAC result string on `;` into an ordered proxy list, non-string/empty ⇒ `[]` (direct). Downloads: `file://` reads from disk via `fileURLToPath`; https adds a bespoke agent carrying the request's CA/rejectUnauthorized/minVersion; axios with `proxy:false` (a PAC fetch must never route through the proxy it configures), maxRedirects 3, status errors become `Failed to fetch PAC (<status>)`.
**Invariant:** `myIpAddress` is OVERRIDDEN with a live NIC scan (first non-internal IPv4, else 127.0.0.1) because the sandbox has no OS network access; evaluation happens inside QuickJS WASM (pac-resolver ≥7) — never eval PAC scripts in the host JS realm; TLS options participate in the cache key ONLY for https-sourced PACs.
**Probe:** `packages/bruno-requests/src/utils/pac-resolver.spec.ts` :55-270 — pins directive splitting, myIpAddress override, https-agent passthrough vs http no-agent, same-wrapper-on-repeats, TTL re-download, empty-array on non-string, readable non-2xx error, file:// paths incl. Windows drive-letter URLs and ENOENT rejection.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "getPacResolver PAC cache", limit: 5 });
// resolves getPacResolver :73-126 + clearPacCache :128-136
```

## Verdict
Adopt promise-cache single-flight + self-evicting failure + semicolon-split result parsing + sandboxed evaluation with injected myIpAddress. Adapt the downloader to your HTTP stack; omit Bruno's specific key format. Coverage caveat: none — clean coverage at pin.
