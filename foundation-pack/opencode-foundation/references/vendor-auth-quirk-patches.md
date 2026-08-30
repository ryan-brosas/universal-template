<!-- capsule-v2 -->
# Vendor auth quirk patches — how do you handle per-vendor auth flows (PKCE loopback, device polling, ADC fetch wrapping, cross-region prefixes) behind one uniform method registry?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Each model vendor has a different auth flow: browser PKCE with a loopback callback, device-code polling, cloud ADC token injection, or IAM credential chains. How do you express all of them as interchangeable integration methods without leaking vendor detail into core?

## Uniform method registration with vendor-owned flows
**Path/Symbol:** `packages/core/src/plugin/provider/openai.ts` (browser method :42-93, headless method :96-138, `exchange` :216-228, `refresh` :230-244, `credential` :252-262, `claim` :276-291), `packages/core/src/plugin/provider/opencode.ts` (`oauth` :47-84, `poll` :247-268, `credential` :270-290, `load`/refresh loop :90-141, public-key gating :160-175), `packages/core/src/plugin/provider/google-vertex.ts` (`resolveProject` :5-12, `resolveLocation` :14-20, `authFetch` :41-54), `packages/core/src/plugin/provider/amazon-bedrock.ts` (`resolveModelID` :15-54, bearer/env handling :67-77).
**Signature:** `IntegrationOAuthMethodRegistration = { integrationID, method: {id, type:"oauth", label}, authorize: () → {mode:"auto", url, instructions, callback: Effect<Credential.OAuth>|Effect<string→Credential>}, refresh: (value) → Effect<Credential.OAuth> }`; key/env methods are `{type:"key"|"env", ...}` with no flow.
**Data Shape:** `Credential.OAuth = {type:"oauth", methodID, refresh, access, expires, metadata?}`; metadata carries vendor extras (accountID, orgID, orgName, server).

### Decisive source
```ts
// plugin/provider/opencode.ts:247-268 — device polling where "pending" is DATA, not failure
const loop = (wait: Duration.Duration): Effect.Effect<Credential.OAuth, unknown> =>
  Effect.gen(function* () {
    yield* Effect.sleep(wait)
    const result = yield* post(http, `${server}/auth/device/token`, {...}, DeviceToken, false) // statusOk=false
    if ("access_token" in result) return yield* credential(http, server, result)
    if (result.error === "authorization_pending") return yield* loop(wait)
    if (result.error === "slow_down") return yield* loop(Duration.sum(wait, Duration.seconds(5)))
    return yield* Effect.fail(new Error(`Device authorization failed: ${result.error}`))
  })
```

**Flow:** All four flows register through the SAME `ctx.integration.transform(draft.method.update(...))` call, so the integration store sees a uniform method list regardless of vendor. openai browser: PKCE (43-char verifier from `crypto.getRandomValues`, S256 challenge), a `node:http` server on localhost:1455 whose handler validates `state` and path, a `Deferred` carrying the code out of the callback thread, and HTML success/error pages from `OauthCallbackPage`; server close is a finalizer. openai headless: device usercode request, then poll with `interval + 3000ms safety margin`; 403/404 mean "not yet" (keep polling), anything else fails. opencode console: device-code flow where the token poll is issued with `statusOk=false` so `authorization_pending`/`slow_down` arrive as DATA (`DeviceToken = Token | TokenPending` union); verification URL is validated as origin-rooted HTTP(S) (rejects malformed like `http://[::1]`); on success it fetches `/api/user` + `/api/orgs` concurrently, picks the first org by (name, id) sort, and stores `{server, accountID, email, orgID, orgName}` in credential metadata — the server URL persists so refresh works against self-hosted consoles. google-vertex: no OAuth method; instead `authFetch` wraps the fetch path for OpenAI-compatible endpoints with a GoogleAuth ADC token (dynamic import, cloud-platform scope) — native Vertex SDK handles ADC internally so its fetch is NOT wrapped. amazon-bedrock: no OAuth method; bearer token resolution is env-first (`AWS_BEARER_TOKEN_BEDROCK` wins over the option; the option is WRITTEN INTO env so the AWS SDK picks it up), else `fromNodeProviderChain` (never gated on explicit env vars — the default chain handles profiles/SSO/instance roles). Refresh implementations always return a full `Credential.OAuth` with the SAME methodID (the host adapter re-pins it). The opencode plugin additionally gates catalog models: without any credential (env OPENCODE_API_KEY, active connection, or configured apiKey), the provider body gets `apiKey: "public"` and every model with `cost.input > 0` is disabled — free models stay enabled.
**Invariant:** core never sees a vendor flow — methods are opaque registrations; every authorize returns `{mode:"auto", url, instructions, callback}`; every refresh returns a full credential with unchanged methodID; pending states are data (union schemas + statusOk=false), never exceptions; credential metadata is the vendor's extension point and survives refresh (`next.metadata ?? value.metadata` in openai.ts refresh).
**Probe:** `packages/core/test/plugin/provider-openai.test.ts` (176L, 7 `it.effect`): "registers browser and headless ChatGPT OAuth methods" pins the exact method list. `packages/core/test/plugin/provider-opencode.test.ts` (483L, 11 `it.effect` + 1 `it.live`): "resolves origin-rooted device verification URLs" + "rejects malformed device verification URLs" pin URL validation; the live test pins bearer-token auth against a stub server and remote catalog projection; "uses a public key and disables paid models without credentials" + "keeps free models without credentials" + "treats output-only cost as free" pin the gating triple. `packages/core/test/plugin/provider-google-vertex.test.ts` (387L, 9 `it.effect`): "does not pass Google auth fetch to the native Vertex SDK" vs "keeps Google auth fetch for OpenAI-compatible Vertex endpoints" pin the wrap boundary. `packages/core/test/plugin/provider-amazon-bedrock.test.ts` (622L, 17 `it.effect`): "loads bearer token option into env and uses bearer auth" + "prefers bearer token env over bearer token option" pin env-first resolution; "creates SDK without explicit credential env so the default AWS chain can resolve credentials" pins the chain fallback. Source pin:
```bash
grep -c 'callbackPort'          packages/core/src/plugin/provider/openai.ts   # expect 4
grep -c 'pollingSafetyMargin'   packages/core/src/plugin/provider/openai.ts   # expect 2
grep -c 'slow_down'             packages/core/src/plugin/provider/opencode.ts # expect 1
grep -c 'withoutCredentials'    packages/core/src/plugin/provider/opencode.ts # expect 4
grep -c 'fromNodeProviderChain' packages/core/src/plugin/provider/amazon-bedrock.ts # expect 2
grep -c 'it.effect'             packages/core/test/plugin/provider-opencode.test.ts # expect 11
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "IntegrationOAuthMethodRegistration authorize callback Deferred PKCE device authorization_pending slow_down authFetch GoogleAuth fromNodeProviderChain AWS_BEARER_TOKEN_BEDROCK public apiKey paid models disabled metadata server orgID", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the uniform method-registration surface with vendor-owned flows, pending-as-data polling unions, metadata as the credential extension point, and the ADC-fetch-wrap boundary (wrap only where the SDK does not handle auth). Adapt the flow specifics to the host's vendors; keep the invariant that refresh preserves metadata and methodID. Omit the concrete vendor endpoints and client IDs (site-specific secrets). Coverage caveat: the openai browser PKCE loopback and headless polling bodies are source-confirmed only (no direct test executes the network flows; the method REGISTRATION is pinned); the opencode live test requires a local Bun server (it.live); Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
