<!-- capsule-v2 -->
# Browser-config projection — how do you hand a runtime config full of live objects to a GUI that can only receive data?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you strip functions/closures from a runtime config and freeze volatile state so a UI process gets a stable, serializable snapshot?

## Function-stripping projection with eager status freeze
**Path/Symbol:** `core/config/load.ts:finalToBrowserConfig` (625–661), `llmToSerializedModelDescription` (598–623); consumed by `ProfileLifecycleManager.getSerializedConfig` (119–141).
**Signature:** `finalToBrowserConfig(final: ContinueConfig, ide: IDE): Promise<BrowserSerializedContinueConfig>` ; `llmToSerializedModelDescription(llm: ILLM): ModelDescription`.
**Data Shape:** output keeps plain-data fields as-is (`ui`, `experimental`, `rules`, `docs`, `tabAutocompleteOptions`) and converts every behavioral member: slash commands lose `run`, context providers collapse to `.description`, tools pass through `serializeTool`, models become `ModelDescription` records.

### Decisive source
```ts
slashCommands: final.slashCommands?.map(({ run, ...rest }) => ({ ...rest, isLegacy: !!run })),
contextProviders: final.contextProviders?.map((c) => c.description),
tools: final.tools.map(serializeTool),
modelsByRole: Object.fromEntries(Object.entries(final.modelsByRole).map(([k, v]) => [k, v.map(llmToSerializedModelDescription)])),
selectedModelByRole: Object.fromEntries(/* same but v ? llmToSerialized(v) : null */),
// llmToSerializedModelDescription freezes volatile state NOW:
{ provider, model, title: llm.title ?? llm.model, apiKey, apiBase, template, completionOptions,
  promptTemplates: serializePromptTemplates(llm.promptTemplates),
  configurationStatus: llm.getConfigurationStatus(),   // <-- method CALL result frozen into data
  roles, envSecretLocations, sourceFile, isFromAutoDetect, toolOverrides }
```

**Flow:** final ContinueConfig → keep data fields verbatim → de-function each list (drop `run` marking legacy via `isLegacy: !!run`, providers→descriptions, tools→serialized) → project every LLM instance to a ModelDescription, evaluating `getConfigurationStatus()` once at projection time → null selections stay null.
**Invariant:** nothing callable crosses the boundary; every capability/status that could change later is snapshotted eagerly so the GUI cannot observe mid-flight mutations; `apiKey`/`apiBase` ARE carried (trust boundary = local IDE socket, not a public wire).
**Probe:** no direct suite at this pin (runner block); source-pinned observable: a slash command WITH `run` projects `{isLegacy: true}` sans `run`; ProfileLifecycleManager caches this result separately from its ContinueConfig slot, so GUI polls reuse the projection without recompiling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "finalToBrowserConfig llmToSerializedModelDescription", limit: 5 });
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.load.finalToBrowserConfig", direction: "inbound", depth: 3 });
// observed inbound: ProfileLifecycleManager.getSerializedConfig -> finalToBrowserConfig
```

## Verdict
Adopt boundary-projection with eager freezing of volatile status and explicit legacy markers instead of shipping live objects; adapt which fields ride along to YOUR trust boundary (do not blindly carry apiKey across processes); omit the role-record typing casts (`// TODO better types here`).
