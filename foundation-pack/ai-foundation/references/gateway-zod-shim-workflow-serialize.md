<!-- capsule-v2 -->
# Gateway zod namespace shim + workflow serialization — why import eleven zod factories and attach static WORKFLOW symbols to a model class?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What do the package's bundle-size and cross-process model-transfer contracts look like in code?

## Named-factory re-export + WORKFLOW_SERIALIZE/DESERIALIZE pair
**Path/Symbol:** `packages/gateway/src/zod.ts` (1–31); `packages/gateway/src/gateway-language-model.ts:WORKFLOW_SERIALIZE/WORKFLOW_DESERIALIZE` statics (37–49).
**Signature:** `export const z = { any, array, boolean, discriminatedUnion, enum, literal, number, object, record, string, union, unknown }` (all from `zod/v4`).
**Data Shape:** Models implement `static [WORKFLOW_SERIALIZE](model)` → `serializeModelOptions({modelId, config})` and `static [WORKFLOW_DESERIALIZE](options)` → `new GatewayLanguageModel(options.modelId, options.config)`. Config captured in the serialized payload INCLUDES the header thunk and fetch override — functions — so serialization is only safe within a process boundary that preserves function references (serializeModelOptions handles this contract).

### Decisive source
```ts
// Import individual Zod factories so bundlers do not retain the full `z`
// namespace and all of its locale exports.
export const z = { any, array, boolean, … };
```
```ts
static [WORKFLOW_SERIALIZE](model: GatewayLanguageModel) {
  return serializeModelOptions({ modelId: model.modelId, config: model.config });
}
static [WORKFLOW_DESERIALIZE](options: {modelId; config}) {
  return new GatewayLanguageModel(options.modelId, options.config);
}
```

**Flow:** workflow engines (e.g. durable-execution integrations) hit the symbols to move live model objects across step boundaries instead of re-calling `createGateway`.
**Invariant:** The shim exists for TREE-SHAKING: `import { z } from 'zod/v4'` pulls locale tables into every consumer bundle; named imports let bundlers drop them. Every schema in the package builds through THIS `z`, so swapping to full-zod silently bloats downstream bundles. The serialize/deserialize pair must stay inverses or workflow replays reconstruct broken models.
**Probe:** `grep -c WORKFLOW_SERIALIZE packages/gateway/src/gateway-language-model.ts` → `2` (import + static). Coverage caveat: no direct unit test drives the statics in gateway package tests (they're exercised by workflow-package integration); verified by read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "WORKFLOW_SERIALIZE GatewayLanguageModel serializeModelOptions", limit: 10 });
```
Resolves line-exact: statics at `gateway-language-model.ts 37-49`.

## Verdict
Adopt the factory-shim pattern in any library importing zod v4 (bundle-size invariant is real and testable); adopt symbol-keyed serialize pair when your models must survive workflow step boundaries; omit the shim if you already tree-shake via `zod/v4-core`.
