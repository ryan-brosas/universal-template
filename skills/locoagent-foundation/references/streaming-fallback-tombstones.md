<!-- capsule-v2 -->
# Streaming fallback tombstones — how do you retry a half-streamed model response without orphaned tool_use blocks or poisoned thinking signatures?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When the stream dies mid-response and a fallback model takes over, how is the partially-emitted state unwound safely?

## streamingFallbackOccured reset block
**Path/Symbol:** `src/query.ts` fallback reset (:708-741), `FallbackTriggeredError` catch (:893-953), `yieldMissingToolResultBlocks` (:123-149), `stripSignatureBlocks` call (:924-929).
**Signature:** `function* yieldMissingToolResultBlocks(assistantMessages: AssistantMessage[], errorMessage: string): Generator<UserMessage>` — emits, per assistant message, one `tool_result` (is_error, `tool_use_id`) per tool_use block with `sourceToolAssistantUUID` set.
**Data Shape:** on trigger: `assistantMessages.length = 0; toolResults.length = 0; toolUseBlocks.length = 0; needsFollowUp = false` — array TRUNCATION in place (references held by the executor stay coherent), plus `streamingToolExecutor.discard()` + a fresh `StreamingToolExecutor`.

### Decisive source
```ts
if (streamingFallbackOccured) {
  // Yield tombstones for orphaned messages so they're removed from UI and transcript.
  // These partial messages (especially thinking blocks) have invalid signatures
  // that would cause "thinking blocks cannot be modified" API errors.
  for (const msg of assistantMessages) { yield { type: 'tombstone' as const, message: msg } }
  assistantMessages.length = 0; toolResults.length = 0
  toolUseBlocks.length = 0; needsFollowUp = false
  if (streamingToolExecutor) {
    streamingToolExecutor.discard()   // prevents orphan tool_results (old ids)
    streamingToolExecutor = new StreamingToolExecutor(...)
  }
}
```

**Flow:** two distinct triggers share the same unwind: (1) mid-stream `onStreamingFallback` callback → tombstone every partial assistant message, truncate all four accumulators, discard+recreate the executor ("This prevents orphan tool_results (with old tool_use_ids) from being yielded after the fallback response arrives"), continue consuming the NEW stream — deliberately NOT reusing first-attempt tool_calls ("we'd have to merge assistant messages with different ids and double up on the tool_results"); (2) thrown `FallbackTriggeredError` with a configured `fallbackModel` → same truncation + `yieldMissingToolResultBlocks('Model fallback triggered')` for any already-yielded tool_use blocks, swap `currentModel`, set `attemptWithFallback = true`, strip signature blocks before retry ("Thinking signatures are model-bound: replaying a protected-thinking block to an unprotected fallback 400s").
**Invariant:** (1) any yielded-but-then-invalidated message must get an explicit tombstone or the transcript keeps ghost content; (2) every emitted tool_use MUST receive SOME tool_result before the loop ends — the error path calls `yieldMissingToolResultBlocks` in three places (fallback throw :900, generic query error :984, user abort non-executor path :1025); (3) never mutate the original streamed `message` objects — backfill runs on a CLONE because the original flows back to the API and byte-mismatch breaks prompt caching (:742-787).
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `grep -n "tombstone" src/query.ts src/types/message.ts | head`; `sed -n '123,149p' src/query.ts` pins the full generator verbatim; `grep -n "thinking blocks cannot be modified" src/query.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "yieldMissingToolResultBlocks", limit: 5, fields: ["signature","name","file"] });
// → locoagent.src.query.yieldMissingToolResultBlocks Function src/query.ts 123-149 (only hit)
```

## Verdict
Adopt tombstone-on-fallback, accumulator truncation, and synthetic tool_result completion as ONE unit; adapt the fallback trigger mechanics to your provider; omit ANT-only signature stripping if your models don't bind thinking signatures. Porting trap: clearing accumulators by REASSIGNING (`assistantMessages = []`) instead of `.length = 0` leaves the executor's captured references pointing at stale arrays.
