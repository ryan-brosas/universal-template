<!-- capsule-v2 -->
# Autocomplete pipeline — how the keystroke-to-ghost-text request is orchestrated and where it can bail

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What is the exact ordered pipeline between a keystroke and a rendered ghost text, and which stages silently return `undefined` instead of surfacing an error?

## The stage-bail completion pipeline
**Path/Symbol:** `core/autocomplete/CompletionProvider.ts:provideInlineCompletionItems` (150–309).
**Signature:** `provideInlineCompletionItems(input: AutocompleteInput, token?: AbortSignal, force?: boolean): Promise<AutocompleteOutcome | undefined>`.
**Data Shape:** `input` carries `completionId`, `filepath`, `pos`, `fileContents`, `fileLines`, `manuallyPassPrefix`; returns an `AutocompleteOutcome` (time, completion, prefix, suffix, prompt, modelProvider, modelName, cacheHit, numLines, gitRepo, uniqueId, timestamp) or `undefined` when any stage bails.

### Decisive source
```ts
const llm = await this._prepareLlm();            // bail: no llm / empty mistral key
if (!llm) return undefined;
if (isSecurityConcern(input.filepath)) return undefined;   // .env etc.
if (!force && await this.debouncer.delayAndShouldDebounce(options.debounceDelay)) return undefined;
if (await shouldPrefilter(helper, this.ide)) return undefined;
const [snippetPayload, workspaceDirs] = await Promise.all([getAllSnippetsWithoutRace({...}), this.ide.getWorkspaceDirs()]);
const { prompt, prefix, suffix, completionOptions } = renderPromptWithTokenLimit({...});
let completion = "";
const cached = helper.options.useCache ? await cache.get(helper.prunedPrefix) : undefined;
if (cached) { completion = cached; cacheHit = true; }
else {
  const stream = this.completionStreamer.streamCompletionWithFilters(token, llm, prefix, suffix, prompt, multiline, completionOptions, helper);
  for await (const update of stream) completion += update;
  if (token.aborted) return undefined;          // never postprocess an aborted stream
  completion = helper.options.transform ? postprocessCompletion({completion, prefix: helper.prunedPrefix, suffix: helper.prunedSuffix, llm}) : completion;
}
if (!completion) return undefined;
```

**Flow:** abort-signal creation → `_prepareLlm` (temperature defaulted to **0.01**, JetBrains model fallback, Mistral empty-key skip, OpenAI legacy-completions flag) → security-concern filepath rejection → debounce (skippable via `force`) → `HelperVars.create` → `shouldPrefilter` → parallel snippet+workspace fetch → token-limited prompt render → LRU cache lookup keyed on **prunedPrefix** → stream with filters → (skip postprocess if aborted) → postprocess → outcome telemetry. Errors in `ERRORS_TO_IGNORE` (`"unexpected server status"`, `"operation was aborted"`) are swallowed silently — "Not worth disrupting the user to tell them that a single autocomplete request didn't go through."

**Invariant:** EVERY stage can bail to `undefined`; latency comes from caching on the pruned prefix and debouncing; correctness comes from never post-processing an aborted stream (the `token.aborted` guard runs before `postprocessCompletion`).

**Probe:** `core/indexing/ignore.ts::isSecurityConcern` — feed a `.env` filepath → returns `undefined` before any LLM call. Cache hit path: same `prunedPrefix` twice → second call sets `cacheHit=true` in the outcome (exercised by `core/autocomplete/util/AutocompleteLruCache.test.ts`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "CompletionProvider provideInlineCompletionItems", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stage-bail pipeline, the pruned-prefix cache key, the abort-before-postprocess guard, and the temperature/security/debounce defaults; adapt model-provider prep and editor transport; omit Continue-specific IDE integrations and onboarding. Coverage caveat: graph metadata is `metadata_match` (indexed 2026-08-16, HEAD is a docs-only change); tests are vitest suites under `core/autocomplete/`.
