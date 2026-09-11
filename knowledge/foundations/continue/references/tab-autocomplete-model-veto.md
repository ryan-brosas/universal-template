<!-- capsule-v2 -->
# Tab-autocomplete model veto — which config mistakes must block a load, and which only warn?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Where is the line between fatal config validation and advisory warnings — specifically for autocomplete model choice?

## Fatal taxonomy + chat-model heuristic veto
**Path/Symbol:** `core/config/validation.ts:validateConfig` (lines 10–164); veto at 48–77; context-window warning at 34–44.
**Signature:** `validateConfig(config: SerializedContinueConfig): ConfigValidationError[] | undefined` (`undefined` ⇒ clean).
**Data Shape:** errors are `{ fatal: boolean, message }`; the same shape flows through the YAML plane's `validateConfigYaml`.

### Decisive source
```ts
const nonAutocompleteModels = [
  // "gpt",      // deliberately disabled — gpt-4-class models were once vetoed, now allowed
  // "claude",
  "mistral",
  "instruct",
];
if (nonAutocompleteModels.some((m) => modelName.includes(m)) &&
    !modelName.includes("deepseek") && !modelName.includes("codestral") &&
    !modelName.toLowerCase().includes("coder")) {
  errors.push({ fatal: false, message: `${modelDescription.model} is not trained for tab-autocomplete,
    and will result in low-quality suggestions. ...` });
}
// window sanity: leaving <1000 tokens for input is a warning, not an error
if (model.contextLength && model.completionOptions?.maxTokens) {
  const difference = model.contextLength - model.completionOptions.maxTokens;
  if (difference < 1000) { errors.push({ fatal: false, message: `...leaves only ${difference} tokens...` }); }
}
```

**Flow:** structural mistakes are **fatal** (models not an array; missing/empty title or provider; slashCommands/contextProviders wrong type or missing name/description; embeddingsProvider/reranker not objects; boolean flags not booleans). Judgment calls are **non-fatal** (chat-model-shaped names on the autocomplete role; tight context windows). Fatal errors trip the loader's single interrupt gate; non-fatal ones ride along in `ConfigResult.errors`.
**Invariant:** the veto matches *substrings of the lowercased model id* with explicit exemption substrings (`deepseek`, `codestral`, `coder`) — comment lines show vetoes are policy that changes over time (gpt/claude disabled), so keep them data, not code structure.
**Probe:** no dedicated suite exists for `validation.ts` itself (coverage caveat); behavior is pinned indirectly by `core/config/yaml/loadYaml.vitest.ts` (schema acceptance) and by the ladder capsule's interrupt test. Direct probe once deps install: `npm run vitest -w core -- validation` after adding one.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", qn_pattern: "continue\\.core\\.config\\..*", detail: "ids", limit: 150 });
// inventory shows validateConfig + validateTabAutocompleteModel as the only validation entries;
// validateTabAutocompleteModel is a closure inside validateConfig (core/config/validation.ts), not exported
```

## Verdict
Adopt the two-tier error taxonomy wired to a single interrupt gate and keep heuristic vetoes as editable string lists with exemptions; adapt the specific name lists to your era's models; omit the JSON-era field checks if your config is schema-validated upstream.
