<!-- capsule-v2 -->
# Runtime API-key plumbing — how does a request find its key when registration, config files, and env vars all exist?

**Source:** pi-hypercharm-provider MIT `main@4520704` (pass 4); Codebase Memory project `pi-hypercharm-provider`. **Question:** Where does the API key come from at each layer (provider registration vs stream call vs status fetches), who writes it, and what happens when it is missing?

## cachedApiKey single-writer + placeholder duality
**Path/Symbol:** `index.ts:420` (`let cachedApiKey`), `index.ts:423-425` (`resolveApiKey`, sole writer per graph USAGE/WRITES edges), session_start call site `index.ts:1047-1050`; fail-fast consumer `index.ts:575-581` (`streamHypercharm`); registration placeholder `index.ts:1003` (`makeProviderConfig`).
**Signature:** `async function resolveApiKey(modelRegistry: ModelRegistry): Promise<void>`; consumer expression `(options as any)?.apiKey || cachedApiKey || ""`.
**Data Shape:** one module-level `string | undefined`; written exactly once per session from pi's `ModelRegistry.getApiKeyForProvider("hypercharm") ?? undefined`. Five readers: `streamHypercharm`, `refreshCredits`, `refreshAccountMeta`, `handleStatusCommand`, `configureStatusInteractive`.

### Decisive source
```ts
let cachedApiKey: string | undefined;

async function resolveApiKey(modelRegistry: ModelRegistry): Promise<void> {
	cachedApiKey = await modelRegistry.getApiKeyForProvider(PROVIDER_ID) ?? undefined;
}

// inside streamHypercharm:
const apiKey = (options as any)?.apiKey || cachedApiKey || "";
if (!apiKey) {
	throw new Error(
		`No API key for HyperCharm. Add it to ~/.pi/agent/auth.json, ` +
		`set HYPERCHARM_API_KEY env var, or use --api-key.`,
	);
}
```
Registration side declares a *placeholder*, not a key:
```ts
return {
	baseUrl: BASE_URL,
	apiKey: "$HYPERCHARM_API_KEY", // pi config-value syntax, resolved by the host
	api: "hypercharm",
	models,
	streamSimple: streamHypercharm,
};
```

**Flow:** session_start bumps epoch → aborts old controllers → fires `resolveApiKey(ctx.modelRegistry).then(...)`; only after the promise resolves do gated prefetch + background revalidation run (both consume the now-cached key) → at request time `streamHypercharm` prefers an explicit `options.apiKey` override, falls back to the cache, and THROWS synchronously if both are empty.
**Invariant:** the registered provider config NEVER contains the real key — the `"$HYPERCHARM_API_KEY"` string is pi config-value syntax resolved by the host for registration purposes, while actual HTTP calls use `cachedApiKey` resolved through the host's ModelRegistry (which itself honors auth.json/env). The empty-string fallback plus throw means a keyless request fails LOUDLY at the moment it matters with all three remediation paths named — it is a user-visible request error raised inside the streamSimple invocation, not a crash of the extension host. Because the cache is written once per session and never mutated elsewhere, no reader can observe a torn write; the epoch guard on the `.then()` (see stale-ctx-epoch-guard.md) stops a replaced session's resolution from prefetching against stale ctx.
**Probe:** runtime event path has no upstream test runner — deterministic probe P-AUTH executed this pass: `node -e` replicating the three-step truthiness ladder (`"override"||"cache"||""`→override; `undefined||"cache"`→cache; `undefined||""`→throw path) returned override/cache/throw respectively; source-read pins :420-425/:575-581/:1003. Record as coverage caveat.
**Coverage caveat:** cited paths verified `no_recorded_issue` via check_index_coverage @ generation 2026-08-24T14:05:13Z; untested upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "pi-hypercharm-provider",
  query: "MATCH (a)-[r:USAGE|WRITES]->(b) WHERE b.name = 'cachedApiKey' RETURN type(r), a.qualified_name, b.qualified_name" });
// → WRITES from resolveApiKey; USAGE from commitPending/configureStatusInteractive/handleStatusCommand/streamHypercharm
```

## Verdict
Adopt the single-writer cache + request-time fail-fast throw pattern and the "placeholder in registration, real key only at call time" split. Adapt the resolution source to your host's credential registry. Omit the HyperCharm-specific remediation strings.
