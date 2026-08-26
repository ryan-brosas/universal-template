<!-- capsule-v2 -->
# Next-edit prediction — sentinel-token editing prompts and the model-specific provider/diff architecture

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does Continue predict the user's NEXT EDIT (in-place modification, not suffix completion), and how is the model-specific prompt/outcome machinery factored so two very different model families share one state machine?

## Editing, not completing: sentinel-token prompting
**Path/Symbol:** `core/nextEdit/constants.ts` (whole), `core/nextEdit/NextEditProvider.ts:provideInlineCompletionItems` (260–302).
**Signature:** `NextEditProvider.provideInlineCompletionItems(input, token, opts?: {withChain, usingFullFileDiff}): Promise<NextEditOutcome | undefined>`.
**Data Shape:** sentinel tokens in `constants.ts` — Instinct: `INSTINCT_USER_CURSOR_IS_HERE_TOKEN` `<|user_cursor_is_here|>`, `INSTINCT_EDITABLE_REGION_START/END_TOKEN`, `INSTINCT_CONTEXT_FILE_TOKEN`, `INSTINCT_SNIPPET_TOKEN`; Mercury Coder: `MERCURY_CODE_TO_EDIT_OPEN/CLOSE`, `MERCURY_CURSOR`, `MERCURY_CURRENT_FILE_CONTENT_*`, `MERCURY_EDIT_DIFF_HISTORY_*`, `MERCURY_RECENTLY_VIEWED_CODE_SNIPPET*`. Shared `UNIQUE_TOKEN = "<|!@#IS_NEXT_EDIT!@#|>"`. Feature gate: `IS_NEXT_EDIT_ACTIVE = false` (constants.ts:3) — the whole mechanism ships dormant behind one boolean.

### Decisive source
```ts
export const IS_NEXT_EDIT_ACTIVE = false;
export const NEXT_EDIT_EDITABLE_REGION_TOP_MARGIN = 0;
export const NEXT_EDIT_EDITABLE_REGION_BOTTOM_MARGIN = 5;
export const MODEL_WINDOW_SIZES = { "mercury-coder": {topMargin:0,bottomMargin:5}, instinct:{topMargin:1,bottomMargin:5} };
```
`INSTINCT_SYSTEM_PROMPT` is instructions-first: "Your role as an AI agent is to help developers complete their code tasks by predicting the next edit that they will make within the section of code marked by `<|editable_region_start|>` and `<|editable_region_end|>` tags... The developer may have stopped in the middle of typing." Output contract: "Provide only the revised code within the tags. Do not include the tags in your output."

**Flow:** `NextEditProvider` is a **singleton** (`initialize`/`getInstance`) — it owns the next-edit state machine (abort signals, edit chains, logging). `provideInlineCompletionItems` → security check → `_initializeCompletionRequest` (abort signal, debounce, `_prepareLlm`, **`modelSupportsNextEdit` capability gate**, `shouldPrefilter`) → `NextEditProviderFactory.createProvider(helper.modelName)` selects Instinct vs MercuryCoder → `_generatePrompts` (snippets + workspace in parallel, `calculateEditableRegion`, combined diff context incl. in-progress edits, `createDiff` history) → `_handleCompletion` (optional unique-token injection, `llm.chat` with `stream:false`, `modelProvider.extractCompletion`, then the **shared `postprocessCompletion`**).

**Invariant:** the singleton guarantees one coherent next-edit state machine; model-specific prompt-building and outcome extraction live in `BaseNextEditModelProvider` subclasses (Instinct/MercuryCoder), NOT in the provider; every model must pass `modelSupportsNextEdit` before any request.

## Model-specific providers + diff-based outcomes
**Path/Symbol:** `core/nextEdit/providers/BaseNextEditProvider.ts` (whole, 470L), `NextEditProviderFactory.ts` (whole).
**Signature:** `abstract class BaseNextEditModelProvider` with abstract `getSystemPrompt/generatePrompts/extractCompletion/buildPromptContext/buildPromptMetadata/getWindowSize/calculateEditableRegion`; concrete `handlePartialFileDiff`/`handleFullFileDiff`; `NextEditProviderFactory.createProvider(modelName)` returns `MercuryCoderProvider` if name includes `NEXT_EDIT_MODELS.MERCURY_CODER`, else `InstinctProvider`, else throws.
**Data Shape:** `handleFullFileDiff` runs `myersDiff(fileSlice, nextCompletion)`, `groupDiffLines(..., 5)`, filters `isWhitespaceOnlyDeletion`, finds the diff group containing the cursor, returns a `NextEditOutcome` for it, and enqueues the OTHER groups into `PrefetchQueue` (warmed predictions ahead of the cursor). `calculateOptimalEditableRegion` grows the editable region symmetrically around the cursor up to a `maxTokens` budget (tokenizer or `length/4` heuristic).

**Flow:** for full-file-diff models (Mercury), the completion is diffed against the file slice; the cursor-local diff group becomes the immediate suggestion and the rest are prefetched; for partial-file-diff models (Instinct), the editable region is replaced directly. `createNextEditOutcome` assembles the outcome (elapsed, model, completion, cursor positions, editable region, diffLines).

**Invariant:** the cursor's diff group is always returned immediately while non-cursor groups are prefetched (never dropped); whitespace-only deletions are filtered out; the editable region never exceeds the token budget.

**Probe:** `core/nextEdit/templating/NextEditPromptEngine.vitest.ts` (`NEXT_EDIT_MODEL_TEMPLATES` contains templates for all supported models; mercury-coder and instinct templates contain expected tokens; `getTemplateForModel` routes by model); `core/nextEdit/templating/instinct.vitest.ts`, `mercuryCoderNextEdit.vitest.ts`, `core/nextEdit/context/diffFormatting.vitest.ts`, `core/nextEdit/diff/diff.vitest.ts`, `core/nextEdit/DocumentHistoryTracker.vitest.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "NextEditProvider provideInlineCompletionItems BaseNextEditModelProvider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-token editing vocabulary, the model-specific provider factory, the singleton state machine, the diff-group cursor/prefetch split, and the shared postprocess gate; adapt the model families/token sets and window margins to host; omit Continue-specific IDE wiring and the dormant `IS_NEXT_EDIT_ACTIVE` flag until a target needs it. Coverage caveat: graph metadata `metadata_match`; `IS_NEXT_EDIT_ACTIVE=false` means this ships dormant.
