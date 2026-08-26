<!-- capsule-v2 -->
# NextEdit prompt assembly + unique-token injection + fine-tuned prompts[1] dispatch

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How are model-specific prompts assembled from shared context, and how does one call site serve both instruct pairs and fine-tuned single-prompt endpoints?

## Key facts
**Path/Symbol:** `core/nextEdit/NextEditProvider.ts` — `_generatePrompts` (:362-437), unique-token injection (:458-467), `llm.chat` dispatch with `stream:false` comment (:469-479), postprocess gate (:481-501); `core/nextEdit/NextEditProviderFactory.ts` (whole, 16L).
**Signature:** `_generatePrompts(helper, opts?) → {editableRegionStartLine, editableRegionEndLine, prompts: Prompt[]}`; factory `NextEditProviderFactory.createProvider(modelName)` → substring-routes mercury-coder→MercuryCoderProvider, instinct→InstinctProvider, else `throw new Error("Unsupported model: ...")`.
**Data Shape:** `ModelSpecificContext = {helper, snippetPayload, editableRegionStartLine/EndLine, diffContext: combinedDiffContext[], autocompleteContext, historyDiff}`; `Prompt = {role: "system"|"user", content: string}`.

### Decisive source
```ts
// :396-409 — finalized diffs + the user's UN-finalized typing both feed the prompt
const combinedDiffContext = [...this.diffContext];
try {
  const inProgressDiff = EditAggregator.getInstance().getInProgressDiff(helper.filepath);
  if (inProgressDiff) combinedDiffContext.push(inProgressDiff);
} catch (e) { /* EditAggregator may not be initialized yet, ignore */ }

// :458-476 — token appended to LAST prompt's string content; endpoint picks pair vs single
if (this.modelProvider.shouldInjectUniqueToken()) {
  const lastPrompt = prompts[prompts.length - 1];
  if (lastPrompt && typeof lastPrompt.content === "string")
    lastPrompt.content += uniqueToken;                 // Mercury <|!@#IS_NEXT_EDIT!@#|>
}
const msg = await llm.chat(
  this.endpointType === "fineTuned" ? [prompts[1]] : prompts,
  token, { stream: false });                           // Mercury cannot stream
```

**Flow:** snippets (`getAllSnippetsWithoutRace` — upstream notes it costs no more than the raced variant) and workspace dirs resolve in parallel → provider's `calculateEditableRegion` → combined diff context → provider's `generatePrompts(context)` renders via its own `PromptTemplateRenderer` (Instinct adds a 25-line cursor window clamp inside `buildPromptContext`; Mercury uses basename paths and recently-viewed blocks) → `buildPromptMetadata` RE-RENDERS the same user prompt for telemetry → inject unique token if the model demands it → chat → `extractCompletion` (Instinct: identity; Mercury: slice between "```\n" and "\n```" markdown fences) → shared `postprocessCompletion` gate before any outcome is built.

**Invariant:** the unique token is appended to the LAST prompt only and only when content is a plain string — a porter who prepends it, or injects into array-content prompts, breaks Mercury's sentinel contract. `prompts[1]` indexing is the fine-tuned-endpoint contract: index 1 is ALWAYS the user prompt because every provider returns `[system, user]`. Postprocessing is shared with autocomplete and runs BEFORE outcome construction — filtered completions produce NO outcome row at all.

**Probe:** `grep -c 'shouldInjectUniqueToken' core/nextEdit/NextEditProvider.ts core/nextEdit/providers/BaseNextEditProvider.ts core/nextEdit/providers/MercuryCoderNextEditProvider.ts core/nextEdit/providers/InstinctNextEditProvider.ts` → 1+1+1+1=4 lines (Mercury also overrides `getUniqueToken` :39, Instinct comments at :35); `grep -c 'prompts\[1\]' core/nextEdit/NextEditProvider.ts` → 2 (:470 comment + :474 dispatch); `grep -cF 'message.lastIndexOf' core/nextEdit/providers/MercuryCoderNextEditProvider.ts` → 1; `grep -c 'getAllSnippetsWithoutRace' core/nextEdit/NextEditProvider.ts` → 3.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "createProvider generatePrompts shouldInjectUniqueToken extractCompletion", limit: 8 })`

## Verdict
Adopt the two-shape prompt contract ([system,user] pair; last-prompt token suffix), the metadata re-render for logging, and the fence-slice extraction pattern. Adapt window sizes/fence markers per model family; never let extraction skip the shared postprocess gate.
