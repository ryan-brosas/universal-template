<!-- capsule-v2 -->
# FIM templating with token-budget pruning — per-model templates that never touch the cursor region

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does Continue build the FIM prompt (prefix/suffix/snippets) per model, and how does it prune to a token budget without cutting the immediate cursor context?

## Template selection + prompt assembly
**Path/Symbol:** `core/autocomplete/templating/index.ts:renderPromptWithTokenLimit` (212–315), `renderPrompt` (100–155), `buildPrompt` (158–201).
**Signature:** `renderPromptWithTokenLimit({snippetPayload, workspaceDirs, helper, llm}): {prompt, prefix, suffix, completionOptions}`.
**Data Shape:** `getTemplate(helper)` returns either a user Handlebars override (`helper.options.template`) or `getTemplateForModel(helper.modelName)`; templates are either a Handlebars string or a function; `compilePrefixSuffix` is an optional custom prefix/suffix compiler.

### Decisive source
```ts
function pruneLength(llm, prompt): number {
  const contextLength = llm.contextLength;
  const reservedTokens = llm.completionOptions.maxTokens ?? DEFAULT_MAX_TOKENS;
  const safetyBuffer = getTokenCountingBufferSafety(contextLength); // min(1000, contextLength*0.02)
  const maxAllowedPromptTokens = contextLength - reservedTokens - safetyBuffer;
  return countTokens(prompt, llm.model) - maxAllowedPromptTokens;
}
// in renderPromptWithTokenLimit, when prune > 0:
const dropPrefix = Math.ceil(tokensToDrop * (prefixTokenCount / totalContextTokens));
const dropSuffix = Math.ceil(tokensToDrop - dropPrefix);
prefix = pruneLinesFromTop(prefix, Math.max(0, prefixTokenCount - dropPrefix), helper.modelName);
suffix = pruneLinesFromBottom(suffix, Math.max(0, suffixTokenCount - dropSuffix), helper.modelName);
// then rebuild the prompt with the pruned prefix/suffix
```

**Flow:** `preparePromptContext` picks prefix (`manuallyPassPrefix || prunedPrefix`), suffix (empty→`\n`), reponame (basename of first workspace dir), template, and snippets (`getSnippets`). `buildPrompt` applies `compilePrefixSuffix` if present, else formats snippets and prepends them to the prefix, then renders the template (Handlebars string or function). `renderPromptWithTokenLimit` computes how many tokens over budget the prompt is, proportionally drops prefix/suffix tokens (weighted by their share of context), and prunes **lines from the top of the prefix** and **lines from the bottom of the suffix** — preserving the cursor-nearest lines. Stop tokens come from `getStopTokens(completionOptions, lang, modelName)`.

**Invariant:** pruning removes SNIPPETS/prefix-top/suffix-bottom, never the immediate cursor region; the token budget is `contextLength - reservedTokens(maxTokens) - safetyBuffer(min(1000, 2% of context))`; prefix is pruned from the top and suffix from the bottom so the cursor-adjacent text survives; `pruneLinesFromTop`/`pruneLinesFromBottom` (countTokens.ts:282/311) account for newline tokens and use index arithmetic, not array mutation.

**Probe:** `core/autocomplete/templating/__tests__/renderPrompt.vitest.ts` — "uses manuallyPassPrefix when provided", "falls back to prunedPrefix", "handles function template", "applies compilePrefixSuffix when provided", "prepends formatted snippets when no compiler present", "matches renderPrompt when llm is undefined", "prunes when over token limit".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "renderPromptWithTokenLimit pruneLinesFromTop getTemplateForModel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-model template selection, the proportional prefix/suffix token drop, the prune-from-top/bottom cursor preservation, and the stop-token derivation; adapt the template registry and token-counting model names to host; omit nothing portable. Coverage caveat: graph metadata `metadata_match`; direct vitest suite.
