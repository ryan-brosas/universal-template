<!-- capsule-v2 -->
# azure-responses-twin-deltas — What exactly does the Azure OpenAI Responses twin change relative to the plain openai-responses adapter?

**Source:** pi-mono (MIT) `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** Which request fields, config ladders, and shared-kernel options differ when porting an Azure-hosted Responses endpoint instead of the OpenAI one?

## Twin delta surface
**Path/Symbol:** `packages/ai/src/api/azure-openai-responses.ts` whole 338L — `parseDeploymentNameMap` :29-40, `resolveDeploymentName` :42-50, `normalizeAzureBaseUrl` :186-215, `buildDefaultBaseUrl` :217-219, `resolveAzureConfig` :221-254, `createClient` :256-273, `buildParams` :275-338; twin reference `packages/ai/src/api/openai-responses.ts` `buildParams` :262-347.
**Signature:** `function buildParams(model, context, options: AzureOpenAIResponsesOptions | undefined, deploymentName: string, grammarToolInputProperties?): ResponseCreateParamsStreaming`; `function resolveAzureConfig(model, options?): { baseUrl: string; apiVersion: string }`.
**Data Shape:** env vars `AZURE_OPENAI_DEPLOYMENT_NAME_MAP` (`modelId=deployment,…`, malformed pairs skipped), `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_RESOURCE_NAME`; option twins `azureDeploymentName / azureApiVersion / azureBaseUrl / azureResourceName`.

### Decisive source
```ts
const params: ResponseCreateParamsStreaming = {
    model: deploymentName,          // NOT model.id — deployment resolution first
    input: messages,
    stream: true,
    prompt_cache_key: clampOpenAIPromptCacheKey(options?.sessionId),
    store: false,
};
// normalizeAzureBaseUrl: Azure-host paths rewritten so the SDK appends correctly
if (isAzureHost && (normalizedPath === "" || normalizedPath === "/" ||
    normalizedPath === "/openai" || normalizedPath === "/openai/v1/responses")) {
    url.pathname = "/openai/v1";
    url.search = "";
}
```

**Flow:** resolveDeploymentName: `options.azureDeploymentName` → env map lookup by `model.id` → `model.id`. resolveAzureConfig: baseUrl ladder `options.azureBaseUrl` → `AZURE_OPENAI_BASE_URL` → `https://<resource>.openai.azure.com/openai/v1` from resource name → `model.baseUrl` → THROW with all four remedies named; then normalizeAzureBaseUrl trims trailing slashes, validates URL, detects Azure hosts (`*.openai.azure.com | *.cognitiveservices.azure.com | *.ai.azure.com`) and rewrites bare/openai/responses paths DOWN to `/openai/v1` because the AzureOpenAI SDK appends `/deployments/<deployment>/responses?api-version=…`. Stream shell: apiKey required before any await; grammarToolInputProperties computed ONCE and threaded into BOTH convertResponsesMessages and processResponsesStream; SDK client created with `maxRetries: 0` while the SHARED `retryProviderRequest` wraps `client.responses.create(params, opts).withResponse()`; post-stream `pending` stopReason throws "stream ended without a stop reason", aborted/error rethrow errorMessage; error path deletes `index/partialJson/customInput` scratch from every block before emitting the error event.
**Invariant:** The twin keeps the shared-kernel contracts byte-compatible — same composite tool-call id handling via `convertResponsesMessages(..., AZURE_TOOL_CALL_PROVIDERS)` ({openai, openai-codex, opencode, **azure-openai-responses**}), same reasoning `{effort, summary} + include:["reasoning.encrypted_content"]` block, `max_output_tokens = max(maxTokens, 16)` floor (#6265), `samplingParams` Object.assign LAST. It deliberately DROPS the openai-only planes: no deferred-tools modes (`splitDeferredTools`/additional-tools/tool-search), no `prompt_cache_retention`/`prompt_cache_options`/`service_tier`, no github-copilot/xai reasoning special cases. streamSimple throws synchronously on missing apiKey and maps reasoning `"off"` → undefined effort.
**Probe:** `packages/ai/test/azure-openai-responses-reasoning-replay.test.ts` — GREEN live 2/2 at pin (builds Model inline, replays reasoning items through the shared slot machine). `packages/ai/test/azure-utils.ts` mirrors parseDeploymentNameMap/resolveAzureDeploymentName for suites; `test/azure-openai-base-url.test.ts` pins the base-url rewrite but is BLOCKED at import (generated-catalog fixture gap). Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "azure deployment name map base url normalize responses config", limit: 10, fields: ["signature", "name", "file"] });
```
Live result at pin: `parseDeploymentNameMap` #1 (-41.84), `__env__AZURE_OPENAI_DEPLOYMENT_NAME_MAP` #2, `normalizeAzureBaseUrl` #3 (-39.75), `resolveDeploymentName` #5, `buildDefaultBaseUrl` #6.

## Verdict
Adopt deployment-name indirection (option → env map → model id) and the base-url normalization set — especially rewriting `/openai/v1/responses` back to `/openai/v1` since the SDK owns the suffix path. Adapt the Azure host detector to your gateway vocabulary. Omit nothing silently: if your host needs deferred tools or prompt-cache retention on Azure, that is NEW capability, not a bug fix — the twin intentionally omits those planes.
