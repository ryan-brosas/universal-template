<!-- capsule-v2 -->
# Gateway realtime identity codec — why is a "model" with zero mapping logic still worth a class?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What does GatewayRealtimeModel actually own if the gateway normalizes all events server-side?

## Thin codec + transport config, identity event mapping
**Path/Symbol:** `packages/gateway/src/gateway-realtime-model.ts:GatewayRealtimeModel` (26–96) + `toGatewayRealtimeUrl` (98–105).
**Signature:** `parseServerEvent(raw: unknown): RealtimeModelV4ServerEvent { return raw as … }` / `serializeClientEvent(event): unknown { return event; }`.
**Data Shape:** Config carries `createClientSecret` as an INJECTED HOOK (implemented by the provider closure) — the model never sees credentials. WS URL = baseURL with `http→ws` upgrade + `/realtime-model?ai-model-id=<id>`; model id passed VERBATIM (gateway owns bare→`openai/` qualification); query params are slash-safe so qualified ids need no encoding.

### Decisive source
```ts
// The Gateway normalizes realtime exactly like it normalizes every other modality:
// the client speaks the normalized AI SDK realtime protocol and the Gateway translates
// to and from the upstream provider server-side. This model is therefore a thin identity
// codec over that normalized protocol — only the connection and authentication are
// Gateway-specific.
parseServerEvent(raw: unknown): RealtimeModelV4ServerEvent {
  return raw as RealtimeModelV4ServerEvent;
}
```
```ts
function toGatewayRealtimeUrl(baseURL: string, modelId: string): string {
  const url = new URL(`${baseURL.replace(/^http/, 'ws')}/realtime-model`);
  url.searchParams.set('ai-model-id', modelId);
```

**Flow:** factory builds model (no guard) → browser/server call `doCreateClientSecret` (delegates to injected hook) or `getWebSocketConfig({token,url})` (returns subprotocol list from the shared auth module).
**Invariant:** The identity casts ARE the contract: because the gateway owns provider translation, client-side mapping would corrupt events. The class exists to (1) pin the URL/subprotocol construction, (2) inject credential handling behind `createClientSecret`, (3) give the protocol version a home. `sessionConfig` is intentionally NOT applied at mint time — it flows later via a normalized `session-update` event.
**Probe:** `grep -c 'return raw as RealtimeModelV4ServerEvent' packages/gateway/src/gateway-realtime-model.ts` → `1`; `grep -cF "baseURL.replace(/^http/, 'ws')" packages/gateway/src/gateway-realtime-model.ts` → `1`. Direct tests: gateway-realtime-model.test.ts 'normalized identity codec' describe ('passes server/client events through unchanged', 'passes session-update provider options through unchanged').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewayRealtimeModel doCreateClientSecret getWebSocketConfig identity codec", limit: 10 });
```
Resolves line-exact anchors in `gateway-realtime-model.ts` (whole file indexed; test describe 'normalized identity codec' :132).

## Verdict
Adopt the injected-mook/identity-codec shape when your proxy normalizes a wire protocol server-side; adapt the URL scheme; omit nothing — the temptation to "helpfully" map events locally is exactly what this design forbids.
