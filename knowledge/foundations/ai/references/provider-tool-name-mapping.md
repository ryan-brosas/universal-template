<!-- capsule-v2 -->
# Provider tool name mapping — how do provider-executed tools keep their client-side names when the provider renames them on the wire?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How is the custom↔provider tool-name translation built, and why must unmapped names fall through as identity?

## createToolNameMapping
**Path/Symbol:** `packages/provider-utils/src/create-tool-name-mapping.ts:createToolNameMapping` (:33-66), interface `ToolNameMapping` (:9-27).
**Signature:** `({tools?: Array<LanguageModelV4FunctionTool | LanguageModelV4ProviderTool>, providerToolNames: Record<`${string}.${string}`, string>}): ToolNameMapping` where the mapping exposes `toProviderToolName(custom)` / `toCustomToolName(provider)`.
**Data Shape:** `providerToolNames` keys are PROVIDER TOOL IDS in `provider.tool-id` dotted form, values are the provider's WIRE names; both internal maps are plain Records built once.

### Decisive source
```ts
for (const tool of tools) {
  if (tool.type === 'provider' && tool.id in providerToolNames) {
    const providerToolName = providerToolNames[tool.id];
    customToolNameToProviderToolName[tool.name] = providerToolName;
    providerToolNameToCustomToolName[providerToolName] = tool.name;
  }
}
return {
  toProviderToolName: (customToolName) => customToolNameToProviderToolName[customToolName] ?? customToolName,
  toCustomToolName: (providerToolName) => providerToolNameToCustomToolName[providerToolName] ?? providerToolName,
};
```

**Flow:** only `type:'provider'` tools whose `id` appears in the provider-supplied name table get mapped — function tools (and unknown provider ids) are absent from both maps and therefore resolve to IDENTITY at call time.
**Invariant:** Identity fallback is LOAD-BEARING: stream events arrive with whatever name the provider used, and every lookup site (tool-call assembly, result routing) calls the mappers unconditionally — throwing on unmapped names would break every function-tool event. The id→name indirection exists because providers rename tools by stable id (`provider.tool-id`), not by client-chosen name. Consumers include anthropic + openai-responses language models (the two with renaming providers).
**Probe:** `packages/provider-utils/src/create-tool-name-mapping.test.ts` (round-trip mapping, unmapped identity fallback, function-tools-ignored cases). Coverage note: verified via dedicated suite at this pin.

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"createToolNameMapping toProviderToolName toCustomToolName providerToolNames","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the build-once dual map with identity fallback; adapt the id grammar (`${string}.${string}`) to your provider's naming scheme; omit the provider-tool filter only if your host has no provider-defined tool concept. Direct-test-pinned at this HEAD.
