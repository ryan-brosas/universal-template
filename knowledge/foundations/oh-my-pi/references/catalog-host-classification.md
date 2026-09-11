<!-- capsule-v2 -->
# Host classification — what is the safe vocabulary for "is this endpoint served by vendor X"?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you gate provider quirks when custom providers can point any baseUrl at any upstream?

## Provider-id OR url-marker classes with a bounded clear-on-full cache
**Path/Symbol:** `packages/catalog/src/hosts.ts:KNOWN_HOSTS` (:26), `MAX_URL_HOST_MATCHES` (:77), `hostMatchesUrl` (:90), `modelMatchesHost` (:107), `resolveVertexEndpointHost` (:149).
**Signature:** `modelMatchesHost(model: {provider, baseUrl}, host: KnownHost): boolean`; `hostMatchesUrl(baseUrl|undefined, host): boolean`.
**Data Shape:** `HostClassSpec {providers?: readonly string[], providerPrefixes?: readonly string[] (e.g. xiaomi-token-plan-*), urlMarkers: readonly string[]}` — markers are lowercase ASCII substrings matched case-insensitively via a branchless `(char | 0x20)` compare.

### Decisive source
```ts
// Markers are case-insensitive SUBSTRINGS matched against the base URL, NOT
// parsed hostnames: proxies regularly embed the upstream host in a path
// segment, and the historical call sites all used substring semantics.
// Callers that need strict hostname matching — where a substring false
// positive is dangerous (the Anthropic official-endpoint OAuth gate) —
// parse the URL and compare the hostname themselves. (compat/anthropic.ts:
// isOfficialAnthropicApiUrl requires exact origin or "/" boundary, so
// https://api.anthropic.com.evil.com cannot pass.)
const MAX_URL_HOST_MATCHES = 512;
if (urlHostMatches.size === MAX_URL_HOST_MATCHES) urlHostMatches.clear();

// Multi-region Vertex codes do NOT follow the regional pattern —
// interpolating them yields hosts like eu-aiplatform.googleapis.com that 404.
if (location === "global") return "aiplatform.googleapis.com";
if (location === "eu" || location === "us") return `aiplatform.${location}.rep.googleapis.com`;
```

**Flow:** call site asks `modelMatchesHost({provider, baseUrl}, "deepseekFamily")` → providers list hits first (id implies class regardless of URL) → prefix list → URL markers → per-URL verdict map cached (custom providers contribute arbitrary endpoints at runtime, hence the bounded cache that clears at 512 entries instead of LRU churn).
**Invariant:** (1) substring semantics is the DEFAULT and every auth-sensitive check must opt into hostname parsing explicitly; (2) sibling classes differ by intent — `deepseekDirect` gates first-party-only quirks while `deepseekFamily` matches ANY DeepSeek-operated host; (3) fireworks is URL-only on purpose because its providers route per-model; (4) endpoint-shape predicates (`/deployments/`, `:rawPredict`, `/endpoints/openapi`, dashscope `/compatible-mode`) are path/verb shapes, not vendor hosts.
**Probe:** direct `packages/catalog/test/hosts.test.ts:11` (hostMatchesUrl), `:30` (modelMatchesHost), `:43` (endpoint shape predicates); lookalike-host rejection pinned in `test/build.test.ts:1394–1398`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "KNOWN_HOSTS modelMatchesHost hostMatchesUrl", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the two-tier check (id first, marker second), the substring-default/strict-opt-in split, and the bounded clear-on-full cache; adapt the host table to your vendors; omit the Vertex multi-region host resolver if you don't front Vertex. Coverage caveat: none.
