<!-- capsule-v2 -->
# Gateway client-secret minting — why is the secret route origin-relative and the guard window-based, not path-based?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does a browser get a short-lived WebSocket credential without ever seeing the long-lived gateway key?

## Server-only mint, origin-relative URL
**Path/Symbol:** `packages/gateway/src/gateway-provider.ts:mintClientSecret` (351–387) + `assertGatewayClientSecretServerEnvironment` (664–670).
**Signature:** `const mintClientSecret = async (params: { modelId: string; expiresAfterSeconds?: number; routeKind?: 'transcription' }): Promise<{ token: string; expiresAt?: number }>`.
**Data Shape:** `POST {origin-of-baseURL}/v1/realtime/client-secrets` — resolved via `new URL('/v1/realtime/client-secrets', baseURL)` so it works when baseURL points at `/v4/ai`. Body `{ model, routeKind? , expiresIn? }` with conditional spreads (absent keys stay absent). Response zod: `{ token: string, expiresAt: number|nullish }`.

### Decisive source
```ts
assertGatewayClientSecretServerEnvironment();
// …
function assertGatewayClientSecretServerEnvironment(): void {
  if (typeof globalThis.window !== 'undefined') {
    throw new Error('AI Gateway client secrets must be minted server-side: …');
  }
}
```
```ts
// provider comment pins the boundary placement:
// No server-environment guard here [on experimental_realtime factory]: building the realtime model is just the
// event codec + WebSocket-config helper, which the browser legitimately needs… The server-only boundary is
// enforced on minting itself (`mintClientSecret`).
```

**Flow:** `experimental_realtime.getToken()` / `experimental_transcription.getToken()` → assert server env → resolve long-lived credential → POST mint → return `{token, expiresAt?}`; transcription variant adds `routeKind: 'transcription'` binding + derives the ws URL separately.
**Invariant:** The guard sits on MINTING, not model construction — the browser must be able to build the realtime codec to connect; only the credential-holding operation is forbidden. The mint URL must be origin-relative because baseURL carries the `/v4/ai` API prefix while the mint route lives at `/v1/...` on the origin. `routeKind` is deliberately omitted for realtime mints so older gateways keep accepting them.
**Probe:** `grep -c "typeof globalThis.window !== 'undefined'" packages/gateway/src/gateway-provider.ts` → `1`; `grep -cF "new URL('/v1/realtime/client-secrets', baseURL)" packages/gateway/src/gateway-provider.ts` → `1`. Direct tests: gateway-realtime-model.test.ts 'allows building the realtime codec model in browsers (no minting)' vs 'rejects minting (getToken) in browsers — the credential must stay server-side'; 'wraps getToken auth failures in a GatewayAuthenticationError'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "mintClientSecret assertGatewayClientSecretServerEnvironment", limit: 10 });
```
Resolves line-exact: `mintClientSecret Function 351-387`, `assertGatewayClientSecretServerEnvironment Function 664-670`.

## Verdict
Adopt the mint-vs-connect boundary split for any browser-delegated auth design; adapt the window check to your SSR detector (Next.js has its own); omit the legacy-gateway `routeKind` omission only if you control both ends.
