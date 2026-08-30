<!-- capsule-v2 -->
# Gateway WebSocket subprotocol auth — how does a bearer token cross a handshake that cannot carry headers?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the exact wire contract for smuggling gateway credentials and team scope through `Sec-WebSocket-Protocol`, and why base64url only the team value?

## Shared client/server protocol module
**Path/Symbol:** `packages/gateway/src/gateway-realtime-auth.ts:buildGatewayProtocols` (68–82) + `encodeSubprotocolValue`/`decodeSubprotocolValue` (136–154) + server decoders (93–124).
**Signature:** `getGatewayRealtimeProtocols(token: string, options?: { teamIdOrSlug?: string }): string[]`; `getGatewayRealtimeAuthToken(secWebSocketProtocol?: string | null): string | undefined`.
**Data Shape:** Protocol list = `[marker, 'ai-gateway-auth.<token>'(, 'ai-gateway-team.<base64url(team)>')]`. Markers: `ai-gateway-realtime.v1` / `ai-gateway-transcription.v1` (negotiation echo — some clients require the 101 response to select one of the OFFERED subprotocols). Auth token is sent RAW; team scope is base64url-encoded (`+→-`, `/→_`, padding stripped on encode, re-padded on decode).

### Decisive source
```ts
const protocols = [marker, `${GATEWAY_AUTH_SUBPROTOCOL_PREFIX}${token}`];
if (options?.teamIdOrSlug) {
  protocols.push(`${GATEWAY_TEAM_SUBPROTOCOL_PREFIX}${encodeSubprotocolValue(options.teamIdOrSlug)}`);
}
// Server side — empty token collapses to undefined:
return findProtocol(h, GATEWAY_AUTH_SUBPROTOCOL_PREFIX)?.slice(PREFIX.length) || undefined;
// Malformed team encoding degrades to undefined, never throws:
try { return decodeSubprotocolValue(encoded) || undefined; } catch { return undefined; }
```

**Flow:** client builds protocols → `new WebSocket(url, ...protocols)` → gateway upgrade handler splits the comma-separated header, prefix-matches after trim → token promoted to `Authorization: Bearer …` before the normal auth path.
**Invariant:** Subprotocol values must satisfy the RFC token grammar — that's why the TOKEN is raw (JWTs are dot-separated tokens = valid) while arbitrary TEAM SLUGS get encoded. The module doc pins the budget: keep the whole header under ~8 KiB because intermediaries reject large upgrades. Client encode + server decode live in ONE file so the contract can't drift.
**Probe:** `grep -cF '${GATEWAY_AUTH_SUBPROTOCOL_PREFIX}${token}' packages/gateway/src/gateway-realtime-auth.ts` → `1`; `grep -cF "'='.repeat((4 - (base64.length % 4)) % 4)" packages/gateway/src/gateway-realtime-auth.ts` → `1`. Direct tests: gateway-realtime-auth.test.ts 'round-trips a token produced by getGatewayRealtimeProtocols', 'preserves tokens that contain dots (e.g. JWT/OIDC)', 'returns undefined for malformed encoded team values'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getGatewayRealtimeProtocols buildGatewayProtocols subprotocol", limit: 10 });
```
Resolves line-exact: `buildGatewayProtocols Function 68-82`, `encodeSubprotocolValue Function 136-146`.

## Verdict
Adopt the subprotocol-smuggling pattern wholesale for browser WebSocket auth (it is the only channel browsers leave open); adapt markers/team encoding to your own prefixes; omit nothing — the grammar constraint and negotiation-marker rationale are the porting traps.
