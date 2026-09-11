<!-- capsule-v2 -->
# Pi provider registration — how do you turn ambient env vars into registered model providers when the runtime has no env-based auth of its own?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory MCP NOT connected this session → direct source+test read fallback per AGENTS.md. **Question:** Pi never reads provider credentials from the environment itself — how do you bridge ambient env vars into its ModelRegistry/ModelRuntime without leaking keys into config files?

## Resolve-then-register split
**Path/Symbol:** `packages/harness-pi/src/pi-auth.ts` — `resolvePiEnv` :96–197, `registerPiProviders` :199–345, `registerCustomProviders` :406–470, `pickProviderEnv` :349–364, `hasConfiguredValue` :89–94, `register` :67–74; call site `packages/harness-pi/src/pi-session.ts` :409–425.
**Signature:** `resolvePiEnv({options, env}) => Record<string,string>`; `registerPiProviders({options, resolvedEnv, registries, clientApp?}) => Promise<void>` where registries = `{modelRegistry: ModelRegistry, modelRuntime: ModelRuntime}`.
**Data Shape:** resolved env keys are either the three special prefixes (`AI_GATEWAY_*`, `OPENAI_*`, `ANTHROPIC_*`) or arbitrary `<PREFIX>_API_KEY`/`<PREFIX>_BASE_URL` pairs; registration targets are provider NAME strings (`vercel-ai-gateway`, `openai`, `anthropic`, or `prefix.toLowerCase().replace(/_/g, '-')`).

### Decisive source
```ts
// pi-auth.ts :406–470 — prefix-derived provider registration
async function registerCustomProviders({ customEnv, registries, clientApp }) {
  if (customEnv.AI_GATEWAY_API_KEY) { /* register 'vercel-ai-gateway' with
      User-Agent/x-client-app clientApp headers via createGatewayProviderConfig */ }
  if (customEnv.OPENAI_API_KEY)  { /* register 'openai'  */ }
  if (customEnv.ANTHROPIC_API_KEY) { /* register 'anthropic', ANTHROPIC_AUTH_TOKEN
      becomes headers: { authorization: `Bearer ${...}` } */ }
  for (const [name, apiKey] of Object.entries(customEnv)) {
    if (!name.endsWith('_API_KEY') || !apiKey) continue;
    const prefix = name.slice(0, -'_API_KEY'.length);
    if (prefix === 'AI_GATEWAY' || prefix === 'OPENAI' || prefix === 'ANTHROPIC') continue;
    const provider = prefix.toLowerCase().replace(/_/g, '-');
    const baseUrl = customEnv[`${prefix}_BASE_URL`];
    if (!baseUrl) continue;                    // no base URL ⇒ NOT registered
    await register({ registries, provider, apiKey, config: { apiKey, baseUrl, authHeader: true } });
  }
}
```

**Flow:** `resolvePiEnv` walks customEnv → explicit gateway → string modes (`openai`/`anthropic`/`custom`/`ai-gateway`) → ambient gateway → ambient sweep of every `*_API_KEY`/`*_BASE_URL`/`ANTHROPIC_AUTH_TOKEN` in the process env; `registerPiProviders` re-derives the mode, and for direct/custom modes MERGES resolved env with a fresh `pickProviderEnv(process.env)` sweep (`{ ...pickProviderEnv(process.env), ...env }`) so ambient credentials register even when the resolved blob was scoped; registration is dual-write — `modelRegistry.registerProvider(provider, config)` for config AND `await modelRuntime.setRuntimeApiKey(provider, apiKey)` for the runtime key, so the key lives in the runtime's auth store, not in any serialized model config. `hasConfiguredValue` recurses into objects so an empty legacy `{gateway: {}}` does not count as configured. The gateway config alone carries identity headers (`'User-Agent': clientApp, 'x-client-app': clientApp` — `ai-sdk/harness-pi/<VERSION>`). Call site (pi-session.ts :409–425): resolve once into `resolverEnv` (comment: "Run-scoped env (for the model resolver's gateway fallback heuristic)"), register, then hand `resolverEnv` to `createPiModelResolver` — one env blob drives both registration and later model resolution.
**Invariant:** credentials reach Pi ONLY through `setRuntimeApiKey` (runtime auth store) — never through registered provider config; a `<PREFIX>_API_KEY` without a matching `<PREFIX>_BASE_URL` is silently skipped; explicit modes register ONLY their own provider even when other credentials ambiently exist (pi-auth.test.ts "registers only openai when openai mode is explicit" — providers list is exactly `['openai']`).
**Probe:** direct test `pi-auth.test.ts` 494L read whole-file (18 cases): "registers all known custom providers" pins the anthropic bearer-header shape and gateway client-app headers; "registers arbitrary custom providers with API key and base URL" pins `MISTRAL_*` → provider `mistral`; "does not register providers when no auth is configured" pins the empty sweep (after `clearAmbientProviderCredentials` stubs every `*_API_KEY`/`*_BASE_URL`/`VERCEL_OIDC_TOKEN` env key). Deterministic probes: `grep -n "setRuntimeApiKey(provider, apiKey)" packages/harness-pi/src/pi-auth.ts` → :74; `grep -c "pickProviderEnv(process.env)" packages/harness-pi/src/pi-auth.ts` → `3`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "registerPiProviders setRuntimeApiKey model registry provider prefix", limit: 10 });
```
Graph MCP absent this session — file-level analog: naive "register provider" queries hit only ai-package registry symbols (provider-registry.ts, pass-10 capsules); GREEN: `registerPiProviders`/`setRuntimeApiKey(provider, apiKey)` resolve to exactly one defining file at :199/:74.

## Verdict
Adopt: resolve-then-register split, dual-write (config + runtime key store), prefix-derived provider names with a base-URL-required gate, explicit-mode isolation. Adapt the special-case prefix list to your runtime's built-in providers. Omit the legacy customEnv object shape and the client-app header stamping if you have no gateway identity contract.
