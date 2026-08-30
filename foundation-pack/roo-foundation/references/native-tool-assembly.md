<!-- capsule-v2 -->
# Native tool assembly — how do you build the per-request tools array, including for providers that must SEE every tool but CALL only some?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does roo assemble native + MCP + custom tools per request, and how does it serve Gemini's "all definitions visible, restricted invocation" requirement?

## buildNativeToolsArrayWithRestrictions: filtered array OR all-tools + allowedFunctionNames
**Path/Symbol:** `src/core/task/build-tools.ts:82-169`; consumed by Task attemptApiRequest (`src/core/task/Task.ts:4103-4118`, gated to `apiProvider === "gemini"`).
**Signature:** `buildNativeToolsArrayWithRestrictions(options): Promise<{ tools, allowedFunctionNames? }>`; `includeAllToolsWithRestrictions?: boolean` flips the mode.
**Data Shape:** `filterSettings = { todoListEnabled: apiConfiguration?.todoListEnabled ?? true, disabledTools, modelInfo }`; native tools vary by `supportsImages` (read_file description).

### Decisive source
```ts
if (includeAllToolsWithRestrictions) {
  const allTools = [...nativeTools, ...mcpTools, ...nativeCustomTools]   // UNFILTERED
  const allowedFunctionNames = filteredTools.map(tool => resolveToolAlias(getToolName(tool)))
  return { tools: allTools, allowedFunctionNames }
}
return { tools: filteredTools }   // [...filteredNative, ...filteredMcp, ...nativeCustom]
```
Custom tools load lazily from `<roo-dirs>/tools` via `customToolRegistry.loadFromDirectoriesIfStale(toolDirs)` ONLY when the `customTools` experiment is on.

**Flow:** gather native defs → filter for mode (shared machinery with the execution gate) → collect dynamic MCP server tools → filter those → optionally append custom tools → either return the filtered set (default) or ALL tools plus alias-resolved allowed names. The alias resolution exists because filtered lists may carry renamed aliases while allTools uses canonical names — unresolved, Gemini rejects mismatches against history.
**Invariant:** The two output shapes must name tools IDENTICALLY after alias resolution; history references historical calls by name, so a provider seeing unfiltered defs still needs the allowed-list in canonical space.
**Probe:** `src/core/task/__tests__/native-tools-filtering.spec.ts` ("should filter native tools based on mode restrictions" :5, always-available :105); Gemini restriction path covered at Task.spec level.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "buildNativeToolsArrayWithRestrictions allowedFunctionNames resolveToolAlias", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-source assembly with the dual shape (filtered vs visible-all+allowlist) and lazy experiment-gated custom-tool loading. Adapt provider gating (Gemini-only today). Omit MCP hub plumbing beyond the getMcpServerTools contract point.
