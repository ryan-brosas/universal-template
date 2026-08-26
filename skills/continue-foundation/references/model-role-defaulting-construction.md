<!-- capsule-v2 -->
# Model role defaulting & construction — how does one YAML model entry become role-assigned LLM instances (and what does AUTODETECT mean)?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you turn declarative model configs into provider LLM objects with correct roles, capabilities, and request options?

## Role defaulting + capability strings + AUTODETECT fan-out
**Path/Symbol:** `core/config/yaml/loadYaml.ts` lines 280–343 (role assignment loop), `core/config/yaml/models.ts:modelConfigToBaseLLM` (50–146), `llmsFromModelConfig` (189–222), `autodetectModels` (148–187).
**Signature:** `llmsFromModelConfig({ model: ModelConfig; uniqueId; llmLogger; config: ContinueConfig }): Promise<BaseLLM[]>`.
**Data Shape:** `modelsByRole` has eight roles: chat, edit, apply, embed, autocomplete, rerank, summarize, subagent.

### Decisive source
```ts
const defaultModelRoles: ModelRole[] = ["chat", "summarize", "apply", "edit"];
for (const model of config.models ?? []) {
  model.roles = model.roles ?? defaultModelRoles;   // unspecified => all four chat-esque roles
  try { const llms = await llmsFromModelConfig({ model, ... });
    if (model.roles?.includes("chat")) continueConfig.modelsByRole.chat.push(...llms);
    ...
  } catch (e) { localErrors.push({ fatal: false, message: `Failed to load model: ...` }); } // skip, don't die
}
// models.ts — capabilities must be UNDEFINED when absent so BaseLLM autodetection can take over:
capabilities: { tools: model.capabilities?.includes("tool_use"),
                uploadImage: model.capabilities?.includes("image_input"),
                nextEdit: model.capabilities?.includes("next_edit") },
// AUTODETECT sentinel fans out to listModels(); the sentinel itself is filtered to stop infinite loops:
if (model.model === AUTODETECT) {
  const modelNames = await llm.listModels();
  const detected = await Promise.all(modelNames.map(async (modelName) =>
    modelName === AUTODETECT ? undefined
      : modelConfigToBaseLLM({ ...model, model: modelName, name: modelName }, ..., isFromAutoDetect: true)));
} // catch => console.warn + [] : a broken listing endpoint degrades to zero models, not a failed load
```

**Flow:** default roles → construct LLM class by `provider` (`LLMClasses.find(c => c.providerName === model.provider)`, unknown ⇒ `undefined` ⇒ empty array) → merge requestOptions (model wins scalars, headers union) → resolve `contextLength` (`model.contextLength ?? defaultCompletionOptions.contextLength`) and `maxTokens` fallback to class defaults → map `env` keys ONE BY ONE via fixed allow-list (`ENV_STRING_KEYS` + boolean `useLegacyCompletionsEndpoint`; comment: "types vary and we don't want to blindly spread env") → fan out per assigned role.
**Invariant:** one bad model never fails the load (non-fatal error, other models proceed); absent capabilities stay undefined (never false) so runtime autodetection still runs.
**Probe:** `core/config/yaml/models.vitest.ts:89–122` asserts merged requestOptions exactly: `{ timeout: 60000, headers: { "user-agent": "Continue/1.0.0", Authorization: "Bearer token123" }, proxy: "model-proxy" }`; line 249 pins unknown-provider graceful handling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "llmsFromModelConfig autodetect models", limit: 10, fields: ["signature"] });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.load.intermediateToFinalConfig", direction: "inbound", depth: 2 });
// callers: loadContinueConfigFromJson, doLoadConfig — same AUTODETECT pattern duplicated on the JSON plane
```

## Verdict
Adopt role defaulting, capability-string mapping with undefined-passthrough, per-key env application, and the AUTODETECT sentinel with its self-loop guard; adapt the provider class registry; omit vscode-only transformers.js embed injection unless you ship local embeddings.
