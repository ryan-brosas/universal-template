<!-- capsule-v2 -->
# customProvider — how do you compose a static model map with a fallback provider without changing failure semantics?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does the SDK let you hand-pick named models (possibly v2/v3 instances) into one provider, and what EXACTLY happens when a lookup misses?

## registry/custom-provider.ts
**Path/Symbol:** `packages/ai/src/registry/custom-provider.ts:customProvider` (:52-252 whole); type helper `ExtractModelId` (:254-257).
**Signature:** `customProvider({ languageModels?, embeddingModels?, imageModels?, transcriptionModels?, speechModels?, rerankingModels?, videoModels?, files?, skills?, fallbackProvider? }): ProviderV4 & { languageModel(id: keyof ...): LanguageModelV4; ... }`.
**Data Shape:** per-family `Record<string, ModelInstance|Specifier>`; `fallbackProvider?: ProviderV2|V3|V4` normalized ONCE via `asProviderV4` at :105-106 (a v2/v3 fallback is upgraded before first use); returned object is `Object.assign(baseProvider, filesAndSkills)` (:251).

### Decisive source
```ts
languageModel(modelId) {
  if (languageModels != null && modelId in languageModels) {
    return resolveLanguageModel(languageModels[modelId]);   // v2/v3 → v4 on demand
  }
  if (fallbackProvider) {
    return fallbackProvider.languageModel(modelId);
  }
  throw new NoSuchModelError({ modelId, modelType: 'languageModel' });
},
```

**Flow:** every family accessor follows ONE three-step ladder — membership check (`modelId in <map>`, so only OWN string keys of the literal record match) → `resolve<Family>Model(entry)` converting specifiers and older specificationVersion instances to V4 lazily → miss falls to the SAME family on `fallbackProvider` → double-miss throws `NoSuchModelError` with `modelType` set. `files()`/`skills()` exist on the returned object ONLY when the local entry or the fallback exposes them; they prefer local (`files ?? fallbackProvider!.files!()`) (:224-249).
**Invariant:** (1) Fallback delegation is PER-FAMILY with an existence guard (`fallbackProvider?.imageModel`) but language/embedding call it unguarded-optional (`fallbackProvider.languageModel(modelId)`) because ProviderV4 requires those two methods — a porter adding a new family must decide which shape their fallback contract has. (2) The fallback receives the ORIGINAL `modelId` — there is no remapping between the custom key namespace and the fallback's ids (tests :75 'should use fallback provider if model not found and fallback exists', v2/v3 conversion of fallback results :88/:100). (3) Resolution happens at CALL time, not construction: entries may be plain strings/specifiers or full v2/v3/v4 instances ('should convert v2 and v3 language models to v4 on demand', test :63). (4) String model ids resolve through the GLOBAL default provider when no custom map matches and no fallback exists — that path lives in `resolve-model.ts` and is exercised by 'string model ids' describe block (test :145). (5) `files`/`skills` presence is TYPE-LEVEL conditional ([FALLBACK] extends …) so TypeScript knows optionality; runtime uses spread-omission (:225-239). Porters who throw from the custom map instead of falling through, or who normalize the fallback eagerly per call, change both error identity and performance.
**Probe:** `bash -c "grep -c 'NoSuchModelError' $REFERENCE_ROOT/ai/packages/ai/src/registry/custom-provider.ts && grep -n 'asProviderV4(fallbackProviderArg)' $REFERENCE_ROOT/ai/packages/ai/src/registry/custom-provider.ts"` → `9` (import + @throws doc + one throw per family accessor) and `:106`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "customProvider fallbackProvider resolveLanguageModel ExtractModelId", limit: 5 });
// → ai.packages.ai.src.registry.custom-provider.customProvider Function packages/ai/src/registry/custom-provider.ts 52-252
```

## Verdict
Adopt the membership→resolve→fallback ladder and lazy version resolution verbatim. Adapt which families your host supports and whether a global default provider exists. Omit the type-level files/skills conditionality if your host has no Files/Skills concept.
