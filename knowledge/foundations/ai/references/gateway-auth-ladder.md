<!-- capsule-v2 -->
# Gateway auth ladder — when is the credential an API key vs a Vercel OIDC token, and what does each failure message owe the user?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does the gateway pick between static API key and ambient OIDC identity, and how does the chosen method change error guidance?

## Two-rung credential ladder
**Path/Symbol:** `packages/gateway/src/gateway-provider.ts:getGatewayAuthToken` (642–662); `packages/gateway/src/vercel-environment.ts:getVercelRequestId` (4–6).
**Signature:** `function getGatewayAuthToken(options: GatewayProviderSettings): Promise<{ token: string; authMethod: 'api-key' | 'oidc' }>`.
**Data Shape:** Rung 1: `loadOptionalSetting({ settingValue: options.apiKey, environmentVariableName: 'AI_GATEWAY_API_KEY' })` — explicit option beats env, and `loadOptionalSetting` treats empty-string env as absent. Rung 2 (only if no key): `await getVercelOidcToken()` from `@vercel/oidc` — this is an async ambient-identity fetch that can itself reject outside Vercel. The `{token, authMethod}` pair flows into `createAuthHeaders`, which stamps `Authorization: Bearer <token>`, `ai-gateway-protocol-version: 0.0.1`, `ai-gateway-auth-method`, optional `x-vercel-ai-gateway-team`.

### Decisive source
```ts
if (apiKey) {
  return { token: apiKey, authMethod: 'api-key' };
}
const oidcToken = await getVercelOidcToken();  // can THROW before any request fires
return { token: oidcToken, authMethod: 'oidc' };
```
```ts
// getHeaders wraps the ladder so pre-request OIDC failures still surface as Gateway errors:
catch (error) {
  throw GatewayAuthenticationError.createContextualError({
    apiKeyProvided: false, oidcTokenProvided: false, statusCode: 401, cause: error,
  });
}
```

**Flow:** request → `getHeaders()` → ladder resolves → headers built with method tag → on ANY ladder throw, wrap in contextual `GatewayAuthenticationError` (never leak the raw OIDC rejection).
**Invariant:** The `authMethod` tag must ride EVERY request (`ai-gateway-auth-method` header) because server-side error mapping (`createGatewayErrorFromResponse`) reads it back via `parseAuthMethod` to decide which remediation text a 401 carries. Porting the key check without the OIDC fallback silently breaks Vercel deployments; porting it without the header breaks error context.
**Probe:** `grep -c 'AI_GATEWAY_API_KEY' packages/gateway/src/gateway-provider.ts` → `2` (settings doc + loadOptionalSetting call). Direct tests: `gateway-provider.test.ts` 'Authentication precedence' block — 'should prefer options.apiKey over AI_GATEWAY_API_KEY', 'should prefer AI_GATEWAY_API_KEY over OIDC token', 'should fall back to OIDC when no API keys are available'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getGatewayAuthToken loadOptionalSetting AI_GATEWAY_API_KEY oidc", limit: 10 });
```
Resolves line-exact: `getGatewayAuthToken Function gateway-provider.ts 642-662` (+ provider-utils `loadOptionalSetting`).

## Verdict
Adopt the two-rung precedence (explicit option → env → ambient identity) and the authMethod-tag-on-every-request contract; adapt the OIDC getter to your platform's identity mechanism; omit the three-option marketing copy in `createContextualError` unless you keep Vercel URLs.
