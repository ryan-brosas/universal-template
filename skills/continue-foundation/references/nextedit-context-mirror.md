<!-- capsule-v2 -->
# NextEdit context mirror — how does next-edit rebuild the autocomplete context pipeline WITHOUT firing a completion, and which two traps hide in it?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you reuse the snippet→renderPrompt machinery for offline/telemetry context, and what does the model-vs-template-name split protect?

## The prefix-returning pipeline twin
**Path/Symbol:** `core/nextEdit/context/autocompleteContextFetching.ts:getAutocompleteContext` (:34-145).
**Signature:** `getAutocompleteContext(filepath, pos, ide, configHandler, getDefinitionsFromLsp = async () => [], recentlyEditedRanges, recentlyVisitedRanges, maxPromptTokens, manuallyPassFileContents, autocompleteModel?: ILLM | string): Promise<string>`.
**Data Shape:** builds a synthetic `AutocompleteInput` (`completionId: "context-fetch-${Date.now()}"`, `isUntitledFile: false`); options ladder `DEFAULT_AUTOCOMPLETE_OPTS ← config.tabAutocompleteOptions ← finalModel.autocompleteOptions ← {maxPromptTokens}`; returns ONLY the rendered `prefix`.

### Decisive source
```ts
if (typeof autocompleteModel === "string") {
  const foundModel = config.modelsByRole.autocomplete.find((m) => m.title === autocompleteModel);
  if (foundModel) { finalModel = foundModel; modelNameForTemplating = foundModel.model; }
  else {
    const configuredModel = config.selectedModelByRole.autocomplete;
    if (!configuredModel) throw new Error("No autocomplete model configured...");
    finalModel = configuredModel;
    modelNameForTemplating = autocompleteModel;   // provided string used for TEMPLATE selection only
  }
}
```
```ts
if (finalModel.promptTemplates?.autocomplete) options.template = finalModel.promptTemplates.autocomplete as string;
const helper = await HelperVars.create(input, options, modelNameForTemplating, ide);
...
const { prompt, prefix, suffix, completionOptions } = renderPrompt({ snippetPayload, workspaceDirs, helper });
return prefix;   // the caller wants the context string, not a completion
```

**Flow:** guard `isSecurityConcern(filepath)` BEFORE any model work → resolve model (instance | title-lookup | fallback-to-configured) keeping TWO names separate: `finalModel` drives nothing here but must exist, `modelNameForTemplating` picks the FIM template — an unconfigured-but-named string still renders with that template via the configured model's plumbing → `HelperVars.create` → `initializeForFile` → `getAllSnippetsWithoutRace` (the UNRACED variant — full fidelity over latency here) → `renderPrompt` → return `prefix`.
**Invariant:** This is the same stage chain as `CompletionProvider.provideInlineCompletionItems` minus debounce/prefilter/stream — drift between the two mirrors silently changes what telemetry thinks the model would have seen. The security gate fires before config loading. Callers pass file contents via `manuallyPassFileContents` so the mirror reads EDITOR state, not disk.
**Probe:** deterministic: `grep -n 'getAllSnippetsWithoutRace' core/nextEdit/context/autocompleteContextFetching.ts` (the unraced variant is load-bearing); consumer pin: `processNextEditData.ts:67-78` calls it with hardcoded `"Codestral"` + randomized token budget (see prev-edit-ledger capsule). Coverage caveat: no dedicated vitest suite at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "getAutocompleteContext renderPrompt HelperVars create", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mirror pattern (re-run context assembly up to prompt render, return the prompt piece) and the model-instance vs template-name split; adapt option laddering to your config shape; omit the IDE/config plumbing. No direct test — pinned by decisive source ranges and its single consumer.
