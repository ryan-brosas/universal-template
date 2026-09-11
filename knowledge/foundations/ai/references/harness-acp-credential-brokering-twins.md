<!-- capsule-v2 -->
# Credential brokering — how do sandbox credentials stay real on the host and structurally-equivalent lies in the sandbox?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** how do you resolve provider profiles ONCE on the host, hand the real values to a request-transformation callback, and still spawn the bridge with an environment that contains NO secret?

## Twin environments (`doStart` :247–303)
**Path/Symbol:** `packages/harness-acp/src/v1/acp-v1-harness.ts` (credentialBrokering branch) + `packages/harness-acp/src/acp-auth.ts`.
**Signature:** broker callback `credentialBrokering({ env }) => RequestTransformation[]`, installed via `sandboxSession.addRequestTransformations(...)` when the capability exists.
**Data Shape:** compatibility is PRE-COMPUTED without touching secret values — `resolveACPProviderAuthenticationCompatibility` (:164–194) records only WHICH env var supplies the credential (`resolveGatewayCredentialSource :206–216` returns `'AI_GATEWAY_API_KEY' | 'VERCEL_OIDC_TOKEN' | null`) plus baseUrl.

### Decisive source
```ts
// acp-v1-harness.ts :279–285 — the verbatim rationale
/*
 * Gateway profiles are resolved on the host twice: real values feed
 * the transformation callback, while the bridge receives only a
 * structurally equivalent environment with credential placeholders.
 * Resolving the profile inside the sandbox would require serializing
 * the Gateway credential into the bridge process environment.
 */
sandboxProviderEnvironment = maskSandboxCredentials({
  environment: resolveProviderEnvironment({
    resolvedProviderAuthentication, clientApp, gatewayApiKey: 'AI_GATEWAY_API_KEY', // placeholder literal
  }),
  credentialEnvironmentVariables,
});
```

**Flow:** resolution ladder (`resolveACPProviderAuthentication` :87–162): explicit/detected direct short-circuits → `auto` with no credential source SILENTLY degrades to direct (:136–141) → gateway selected explicitly without creds THROWS naming both env vars (:142–146) → VERCEL_OIDC_TOKEN resolution RE-RUNS the env resolver scoped to ONLY `{VERCEL_OIDC_TOKEN}` so an ambient `AI_GATEWAY_API_KEY` cannot shadow an intended OIDC flow (:229–232) → with brokering + `addRequestTransformations` support, the broker receives REAL `{...implementationEnvironment, ...providerEnvironment}` while the bridge/child receive masked twins and `AI_SDK_ACP_GATEWAY_API_KEY/_BASE_URL` are stripped from the auth environment (:294–300); without the capability, brokering degrades to `warnCredentialBrokeringUnavailable()` and REAL creds ride the spawn env (legacy path, test :616–645). The bridge child-env builder then strips its OWN control/secret variables from inherited env before launchEnv overrides (`BRIDGE_CHANNEL_TOKEN`, `BRIDGE_WS_PORT`, `AI_SDK_ACP_GATEWAY_*`, `AI_SDK_ACP_CLIENT_APP_*`, config env — index.ts :701–717), and `privateHome` reroutes HOME into the implementation dir prepending `<home>/.local/bin` to PATH (:718–731).

**Invariant:** secrets never sit in stored or spawned config — persisted profiles reference credentials BY NAME via `$source:` interpolation with prefix/suffix/ensureSuffix composition (`gateway-api-key`, `gateway-base-url`, `gateway-authorization ⇒ 'Bearer '+key`, `client-app*`; profile-values.ts :10–97; ensureSuffix strips trailing slashes before comparing). The auth-profile DIGEST hashes stable-stringified CONFIG, not credentials (acp-auth.ts :51–85) — feeding the pass-20 lifecycle gate. Brokering failure aborts BEFORE any attach or spawn (test :647+).

**Probe:** `packages/harness-acp/src/acp-harness.test.ts :482–645` — direct profile: broker sees `'direct-secret'` while spawn env carries the NAME `'PROVIDER_API_KEY'` as value and full-env JSON `.not.toContain('direct-secret')` (:506–526); gateway profile: `$source:'gateway-api-key'` resolves for the broker, spawn env has `AI_SDK_ACP_GATEWAY_API_KEY` undefined and bridge-config carries placeholder providerEnvironment (:581–611).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "resolve gateway credential source authentication profile broker masked environment vercel oidc", limit: 10 });
```
Live @pin: rank#1 `resolveGatewayCredentialSource :206-216` + full acp-auth family (`resolveACPProfileValue`, `createACPAuthenticationProfileIdentity`, `resolveACPProviderAuthentication`).

## Verdict
Adopt: precomputed secretless compatibility, silent auto→direct degradation vs explicit-selection throw, scoped OIDC re-resolution, twin-environment masking behind a capability gate with legacy fallback + warning, control-var stripping in the child env, `$source`-named persisted profiles, config-only digests. Adapt env-var names and transformation shapes to your sandbox. Omit Vercel-specific defaults (`https://ai-gateway.vercel.sh`). Coverage caveat: runner block stands (no node_modules → vitest unrunnable); anchors verified by direct reads at pin.
