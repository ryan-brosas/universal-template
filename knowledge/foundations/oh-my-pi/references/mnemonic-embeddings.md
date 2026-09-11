<!-- capsule-v2 -->
# Mnemonic embedding seam — provider chain, self-heal, runtime install, host LLM bridge

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/mnemopi/src/core/embeddings.ts` + `llm-backends.ts` + `fastembed-runtime.ts`. **Question:** How does a memory layer embed text across optional providers while degrading to null instead of crashing — and heal its own corrupted model cache?

## embed() = four-stage provider chain, success-only caching
**Path/Symbol:** `packages/mnemopi/src/core/embeddings.ts:embedQuery` (550–564), `embed` (567+), `embedApi` (427), `capInputs` (259), `queryCache` (57, LRU); `llm-backends.ts`; `fastembed-runtime.ts`.
**Signature:** `embedQuery(text): Promise<Vector | null>`; `embed(texts): Promise<EmbeddingMatrix | null>`; `available(): Promise<boolean>`; `embeddingDimFor(model): number`. **Data Shape:** `Vector` = float array; `EmbeddingMatrix` = `Vector[]`; `capInputs` bounds batch size; module LRU maps text → vector.

### Decisive source
```ts
export async function embed(texts: readonly string[]): Promise<EmbeddingMatrix | null> {
  if (texts.length === 0 || embeddingsDisabled()) return null;
  texts = capInputs(texts);
  const activeProvider = resolveEmbeddingProvider(activeEmbeddingOptions()?.provider);
  if (activeProvider !== undefined) {
    try { return await collectMatrix(await activeProvider.embed(texts)); } catch { return null; }
  }
  if (providerOverride !== null) { /* same guarded path */ }
  if (isApiModel(defaultModel())) return embedApi(texts);
  if (texts.length === 1) { const cached = queryCache.get(queryCacheKey(texts[0] ?? "")); if (cached !== undefined) return [cached]; }
  const model = await getLocalModel();
  if (model === null) return null;
```

**Flow:** active provider wins → test/provider override → API model (`embedApi`) → local flag-embedding; single-text lookups hit the query LRU before the local model. `embedQuery` caches ONLY successful vectors (`if (vector !== null) queryCache.set(key)`) — a transient outage never poisons recall.

**Invariant:** every path returns `null` instead of throwing (the caller degrades, never crashes); the cache only ever stores successful embeddings; custom base URLs skip the auth gate.

## Local model resolution + self-heal (quarantine inside cache dir only)
**Path/Symbol:** `defaultLocalModelInitializer` (141–160s), `quarantineCorruptModelFile` (78–110), `clearIncompleteModelCache` (112–138).

### Decisive source
```ts
const match = /Load model from (.+?\.onnx) failed:.*Protobuf parsing failed/i.exec(message);
if (!match) return false;
const modelFile = resolve(match[1]); const cacheRoot = resolve(cacheDir ?? getFastembedCacheDir());
if (!modelFile.startsWith(cacheRoot + sep)) return false;   // NEVER rename outside cache
await fsp.rename(modelFile, `${modelFile}.corrupt-${Date.now()}`);  // quarantine, retry once
```

**Flow:** a protobuf parsing error is matched by regex; the offending `.onnx` is renamed aside only if it lives INSIDE the fastembed cache dir; init retries once after the sidecar-heal (`ensureFastembedModelSidecars`); concurrent heal stays safe because renaming an already-vanished file is treated as successful quarantine. `clearIncompleteModelCache` wipes the cache when enough files are missing so a clean re-download happens.

**Probe:** `test/fastembed-runtime.test.ts`, `test/fastembed-model-cache.test.ts`, `test/corrupt-model-quarantine.test.ts`, `test/corrupt-model-retry.test.ts`, `test/embedding-input-cap.test.ts`, `test/degrade-vector.test.ts`, `test/optional-embeddings.test.ts`.

## Remote API route — auth-optional POST with internal retries
**Signature:** `embedApi(texts): Promise<EmbeddingMatrix | null>`.

```ts
const isCustom = !hostMatchesUrl(baseUrl, "openrouter");
const apiKey = embeddingApiKey();
if (!isCustom && !embeddingKeyConfigured(apiKey)) return null;  // openrouter: unconfigured => no API route
const headers = { "Content-Type": "application/json", ...getOpenRouterHeaders() };
if (key !== "") headers.Authorization = `Bearer ${key}`;   // empty static key => local/proxy, no header
// auth wrapper re-resolves on 401 (force-refresh/sibling rotation); fetch retry backs off on 429
```

## Runtime install: exact-pin plan, no eager download
**Path/Symbol:** `fastembed-runtime.ts:fastembedRuntimeInstallPlan` (40).
**Signature:** returns `{ versionKey, install: { dependencies: { fastembed }, trustedDependencies: ["onnxruntime-node"] } }` — versionKey derived from the peerDep spec + `_transitive-ort` so policy changes bust caches; the fastembed pin is an EXACT version in `peerDependencies` (not catalog:) so a bundled binary still carries a concrete spec; the ORT native binding rides along tagged trusted.

## Host LLM bridge — injection-only, no package dependency
**Path/Symbol:** `llm-backends.ts:setHostLlmBackend` (19), `callHostLlm` (31), `CallableLlmBackend` (45).
**Signature:** `setHostLlmBackend(backend: LlmBackend | null): void`; `callHostLlm(prompt, opts): Promise<string | null>`.
**Flow:** the host installs exactly one backend; `callHostLlm` returns null when none configured, on throw, or on non-string result. The seam is injection-only — no LLM dependency enters the package graph.

**Probe:** `test/llm-backends.test.ts`, `test/local-llm.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(embed|embedQuery|embedApi|quarantineCorruptModelFile|clearIncompleteModelCache|fastembedRuntimeInstallPlan|setHostLlmBackend|callHostLlm)$", limit: 12, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.mnemopi.src.core.embeddings.embedApi" });
```

## Verdict
Adopt null-degrading provider chains, success-only embedding caches, regex-matched quarantine confined to the cache root, and injection-only host LLM bridges; adapt provider names, cache dirs, and install plans to host tooling; omit OpenRouter specifics unless targeting that vendor.
