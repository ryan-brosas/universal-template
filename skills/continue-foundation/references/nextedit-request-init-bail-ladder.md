<!-- capsule-v2 -->
# NextEdit request-init bail ladder — every silent `helper: undefined` return and what it skips

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** Where does a next-edit request die BEFORE any LLM call, in what order, and why do most exits return `undefined` instead of raising?

## Key facts
**Path/Symbol:** `core/nextEdit/NextEditProvider.ts` — `_initializeCompletionRequest` (:304-360), `_prepareLlm` (:133-161), `provideInlineCompletionItems` entry guard (:268-270), `ERRORS_TO_IGNORE` (:43-47), `onError` dedupe (:163-177).
**Signature:** `_initializeCompletionRequest(input, token): Promise<{token, startTime, helper: HelperVars | undefined}>` — `undefined` helper = "silently skip this request".
**Data Shape:** bail sites in order: (1) `isSecurityConcern(input.filepath)` → undefined; (2) debounce win (`delayAndShouldDebounce`) → undefined; (3) `_prepareLlm()` returns undefined (no llm, or mistral with empty apiKey); (4) `!modelSupportsNextEdit(llm.capabilities, llm.model, llm.title)` → console.error + undefined; (5) `shouldPrefilter(helper, this.ide)` → undefined. Only thrown errors reach `onError`.

### Decisive source
```ts
// :133-161 — _prepareLlm mutates the shared llm object as a side effect:
if (llm.model === undefined && llm.completionOptions?.model !== undefined)
    llm.model = llm.completionOptions.model;          // JetBrains PR#3022 shim
if (llm.providerName === "mistral" && llm.apiKey === "") return undefined;
if (llm.completionOptions.temperature === undefined)
    llm.completionOptions.temperature = 0.01;         // set, don't override
if (llm instanceof OpenAI && llm.providerName !== "openrouter")
    llm.useLegacyCompletionsEndpoint = true;          // completions, not chat
```
```ts
// core/llm/autodetect.ts:292-311 — capability gate: explicit flag wins,
// else substring match against MODEL_SUPPORTS_NEXT_EDIT = [mercury-coder, instinct]
function modelSupportsNextEdit(capabilities, model, title): boolean {
  if (capabilities?.nextEdit !== undefined) return capabilities.nextEdit;
  return MODEL_SUPPORTS_NEXT_EDIT.some(
    (m) => model.toLowerCase().includes(m) || title?.includes(m));
}
```

**Flow:** security gate → abort-controller registration (own controller via loggingService when no external token; otherwise just `trackPendingCompletion`) → debounce → `_prepareLlm` → pending-completion enrichment (`modelName`, `modelProvider`, `filepath`) → capability gate → optional prompt-template override from `llm.promptTemplates.autocomplete` → `HelperVars.create` → prefilter. Errors surface through `onError`, which drops `ERRORS_TO_IGNORE` ("unexpected server status", "operation was aborted") and de-duplicates everything else through `errorsShown` so one broken config can't spam the user.

**Invariant:** the ladder is ORDERED — debounce precedes llm resolution (a debounced-out request never reads config); the capability gate sits AFTER llm resolution but BEFORE any file work (`HelperVars.create` is never paid for an unsupported model). Silent-undefined is deliberate UX policy: expected failures must not disrupt the user; only first-seen unexpected errors propagate to `_onError`. `_prepareLlm`'s mutations are sticky on the cached ILLM — a porter who clones instead of mutating changes legacy-endpoint behavior for autocomplete too.

**Probe:** `grep -c 'return { token, startTime, helper: undefined }' core/nextEdit/NextEditProvider.ts` → 4; `grep -c 'modelSupportsNextEdit' core/nextEdit/NextEditProvider.ts core/llm/autodetect.ts` → 2+2=4 lines; `grep -cF 'llm.useLegacyCompletionsEndpoint = true' core/nextEdit/NextEditProvider.ts` → 1; `grep -c 'unexpected server status' core/nextEdit/NextEditProvider.ts` → 1.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "modelSupportsNextEdit _initializeCompletionRequest shouldPrefilter", limit: 8 })`

## Verdict
Adopt the ordered bail ladder with capability-gate-before-file-work, and the ignore-list + show-once error funnel. Adapt the JetBrains model shim and mistral-empty-key special case to your host's provider quirks; keep them as explicit, commented exceptions.
