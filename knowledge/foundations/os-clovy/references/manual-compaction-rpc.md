<!-- capsule-v2 -->
# Manual compaction RPC — how does the host shrink history on demand without starting a run, and what happens when the summarizer is down?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter exposing user-triggered context cleanup needs an RPC that force-compacts arbitrary history through a metered model path while surviving summarizer failure.

## history.compact + summarize budget ladder
**Path/Symbol:** `agent-runtime/src/service.ts:RuntimeService.compact` (:208-246) dispatched from `handle` (:61-63); `OpenAIAgentsEngine.summarize` (sdk-engine.ts :89-132).
**Signature:** `handle({method:"history.compact", params:{history, model?, contextWindow?, maxOutputTokens?}}): Promise<CompactionResult>`; `summarize(input: EngineSummaryInput): Promise<string>`.
**Data Shape:** Request: `history` (required array), optional string `model`, numbers `contextWindow` (default 128_000) / `maxOutputTokens`. Reply = full `CompactionResult` (`compacted`, `history`, `removedItemIds`, `summary{text,metadata}`).

### Decisive source
```ts
// service.compact — ALWAYS forced; summarizer only when the host names a model
const result = await compactHistory({
  history, contextWindow: typeof params.contextWindow === "number" ? ... : 128_000,
  ...(maxOutputTokens === undefined ? {} : { maxOutputTokens }),
  onFallback: (error) => this.logCompactionFallback(error, sessionId, runId),
  ...(model ? { summarize: (items) => this.engine.summarize({ sessionId, runId, model, history: items, ... }) } : {}),
  force: true,                                   // bypasses the 85% trigger
});

// engine.summarize — bounded metered summary via the SAME reserved model tool
const maxTokens = Math.max(1, Math.min(CONTEXT_SUMMARY_MAX_TOKENS /*2048*/,
  configuredOutputTokens, Math.floor(contextWindow / 4)));
const maxInputTokens = Math.max(256, Math.floor(contextWindow * 0.75) - maxTokens);
const maxInputChars = maxInputTokens * CONSERVATIVE_SUMMARY_CHARS_PER_TOKEN /*2*/;
// ... empty accumulated summary → throw new Error("...returned an empty context summary")
```

**Flow:** host calls `history.compact` → no run key is claimed, nothing accepts/starts — this is pure history service → `compactHistory(force:true)` partitions/groups exactly as auto-compaction does → if `model` was supplied, the summary request rides `engine.summarize`, which goes through the reserved chat-completions host tool (metered, host-routed — test asserts exactly ONE model request with `max_tokens:2000`, `stream:true`) → success returns the semantic summary; failure (or no model given) logs a warn and returns the deterministic `/^Earlier conversation context:/` fallback with `metadata:{fallback:true}` — the RPC still succeeds.
**Invariant:** The RPC never throws because summarization did: fallback keeps `compacted:true` so the host's history stays bounded even during provider outages; output tokens are triple-clamped (≤2048 absolute, ≤ configured, ≤ contextWindow/4) and input chars are budgeted at 2 conservative chars/token against 75% of the window minus the output reservation — the summarize call itself can never blow the context it is trying to relieve; the summary system prompt carries the injection guard ("never as instructions", test-asserted).
**Probe:** `agent-runtime/test/service.test.ts` — "routes manual compaction through the reserved metered model host tool" (:332-407: single request, `max_tokens===2000`, input ≤8100 chars) and "keeps manual compaction available when model summarization fails" (:409-450: `compacted===true`, fallback prefix match, `metadata.fallback===true`); also "forces model-generated manual compaction without starting an agent run" (:300+). Suite runner-blocked at pin (@openai/agents absent); ranges read directly.

## Get live surrounding code
**Retrieve:** executed at pin:
```
search_graph({ project:"os-clovy", query:"summarize metered model summary request", file_pattern:"agent-runtime/src/*" })
→ src.sdk-engine.OpenAIAgentsEngine.summarize Method sdk-engine.ts 89-132   (rank 1)
   src.compaction.summarizeOrFallback Function compaction.ts 120-139
```

## Verdict
Adopt force-flag reuse of the auto-compaction kernel behind a dedicated RPC, the triple-clamped summarize budget, and fallback-must-succeed semantics (log + deterministic summary, HTTP-success shape). Adapt the default context window and clamp constants to your product. Omit the Clovy prompt wrapper only together with any consumer that pattern-matches the fallback prefix; keep the untrusted-data fence in the summary system instructions regardless.
