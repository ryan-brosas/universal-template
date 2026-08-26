<!-- capsule-v2 -->
# Gateway provider options — why is the routing-options type an open record with a service-side schema?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How can the gateway grow new routing knobs without an SDK release, and which typed keys exist today?

## Open index signature + documented known keys
**Path/Symbol:** `packages/gateway/src/gateway-provider-options.ts:GatewayProviderOptions` (1–55).
**Signature:** `type GatewayProviderOptions = { [key: string]: unknown; byok?: …; caching?: 'auto'; disallowPromptTraining?: boolean; has?: Array<'implicit-caching'|'vision'>; models?: string[]; only?: string[]; order?: string[]; providerTimeouts?: {byok?: Record<string, number>}; quotaEntityId?: string; serviceTier?: 'flex'|'priority'; sort?: 'cost'|'tps'|'ttft'; tags?: string[]; user?: string; zeroDataRetention?: boolean }`.
**Data Shape:** Rides `providerOptions.gateway.*` on model calls. Routing controls: `models` (ordered fallback slugs), `only` (provider allow-list), `order` (attempt order), `sort` (cost|tps|ttft), `has` (capability filter), `serviceTier`, `providerTimeouts.byok` (per-credential ms). Governance: `byok` (request-scoped credentials replacing cached ones), `disallowPromptTraining`, `zeroDataRetention`, `quotaEntityId`, `user`, `tags`.

### Decisive source
```ts
// https://vercel.com/docs/ai-gateway/provider-options
export type GatewayProviderOptions = {
  /**
   * Service-owned options may be added by the Gateway without requiring an SDK
   * release. The Gateway service validates and applies the runtime schema.
   */
  [key: string]: unknown;
```

**Flow:** user sets `providerOptions: { gateway: {...} }` → AI SDK serializes it into the request body → GATEWAY (not the SDK) validates and applies.
**Invariant:** The index signature is the versioning strategy: unknown keys MUST pass through unvalidated client-side because the service schema evolves faster than the package. The comment block is normative documentation, not decoration — removing a "typed" key from this file would not remove the server feature, only local autocomplete.
**Probe:** `grep -c 'ai-o11y-deployment-id' packages/gateway/src/gateway-provider.ts` → unrelated to this file; anchor instead on the header constant in the same plane: `grep -cF "'ai-gateway-auth-method'" packages/gateway/src/gateway-headers.ts` → `1`; for this file: `grep -c "serviceTier?:" packages/gateway/src/gateway-provider-options.ts` → `1`. Coverage caveat: TYPE-ONLY file — no runtime probe or direct test exists; verified by read + tsc consumption in settings docs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "GatewayProviderOptions byok serviceTier zeroDataRetention", limit: 10 });
```
Module resolves via `search_code`/BM25 on member names (`gateway-provider-options.ts` indexed whole).

## Verdict
Adopt open-record-with-documented-keys for any client of a fast-moving service API; adapt key names; omit nothing — closing the record is the classic porting mistake that turns service additions into hard client errors.
