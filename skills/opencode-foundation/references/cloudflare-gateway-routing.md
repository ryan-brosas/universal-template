<!-- capsule-v2 -->
# Cloudflare AI Gateway routing & Workers-AI auth boundary — which models ride native passthrough SDKs, and who carries the upstream token?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100` (drift wave: `provider.ts` :101-105/:838-857/:1226-1236/:1246-1252/:1474-1479; `transform.ts` qwen default-temp removal). **Question:** How does one gateway provider serve OpenAI, Anthropic, and third-party models through their correct APIs without leaking the gateway's own credentials to third parties?

## The three-route getModel ladder
**Path/Symbol:** `packages/opencode/src/provider/provider.ts` custom cloudflare-ai-gateway loader `getModel` (:839-857); npm override `cloudflareGatewayNpm` (:1226-1236); Vertex endpoint helper `googleVertexEndpoint` (:101-105).
**Signature:** route by modelID PREFIX: `openai/… → createOpenAI()(rest)`; `anthropic/… → createAnthropic()(rest)`; `workers-ai/… | @cf/… → createUnified({apiKey: CF-token})`; anything else → `createUnified({})` (NO key).
**Data Shape:** passthrough wrappers inject a `CF_TEMP_TOKEN` sentinel the gateway strips before dispatch (Unified Billing / stored BYOK keeps upstream billing on the gateway); Workers AI is the ONLY first-party provider whose upstream IS Cloudflare, so it alone receives the real token as upstream Authorization.

### Decisive source
```ts
// provider.ts:846-853 — prefix routing + the only-keyed-upstream rule
if (modelID.startsWith("openai/")) return aigateway(createOpenAI()(modelID.slice("openai/".length)))
if (modelID.startsWith("anthropic/")) return aigateway(createAnthropic()(modelID.slice("anthropic/".length)))
...
const isWorkersAi = modelID.startsWith("workers-ai/") || modelID.startsWith("@cf/")
const unified = createUnified(isWorkersAi ? { apiKey: *** } : {})
```

And the catalog-side twin — reasoning VARIANTS must produce payloads the native SDK understands, so the npm override fires BEFORE variant computation:
```ts
// provider.ts:1228-1235
function cloudflareGatewayNpm(providerID: string, modelID: string) {
  if (providerID !== "cloudflare-ai-gateway") return undefined
  if (modelID.startsWith("openai/")) return "@ai-sdk/openai"
  if (modelID.startsWith("anthropic/")) return "@ai-sdk/anthropic"
  return undefined
}
```
wired at BOTH model-construction sites (:1250 fromModelsDevModel and :1477 config-defined models, each ahead of `modelsDev[providerID]?.npm ?? "@ai-sdk/openai-compatible"`).
**Flow:** new OpenAI models reject tools+reasoning_effort on chat completions — riding @ai-sdk/openai gives them the Responses API, anthropic/* gets Messages. Variants (`reasoning_effort` vs anthropic `effort`) are computed against the resolved npm, hence the override must apply in both the catalog path AND the config-defined path or config models silently fall back to openai-compatible shapes. Vertex loader separately gained eu/us replicated endpoints (`aiplatform.{eu,us}.rep.googleapis.com`) alongside global (:101-105). transform.ts dropped the blanket qwen temperature=0.55 default (qwen now follows generic reasoning paths :788/:1248 comments).
**Invariant:** Third-party providers behind the gateway must NEVER receive the Cloudflare token — a porter that passes apiKey uniformly leaks stored/BYOK credentials to every upstream. The npm override is LOAD-BEARING for variant payloads, not cosmetic.
**Probe:** direct pins (execute from repo root):
```bash
grep -n 'cloudflareGatewayNpm' packages/opencode/src/provider/provider.ts
grep -n 'googleVertexEndpoint' packages/opencode/src/provider/provider.ts
grep -c 'id.includes("qwen")' packages/opencode/src/provider/transform.ts
```
expect :1233/:1250/:1477 and :101/:531 respectively; transform count = 1 (the reasoning-skip list at :788 — temperature default REMOVED).
Direct test: `packages/opencode/test/plugin/cloudflare.test.ts` + `packages/web/src/content/docs/go.mdx` pricing docs updated in same wave.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "cloudflare ai gateway unified workers-ai passthrough", limit: 6 });
```

## Verdict
Adopt prefix-routed passthrough with single-first-party-key discipline and the pre-variant npm resolution; adapt provider ids/npm names to host catalog; omit Cloudflare-specific billing sentinel details.
