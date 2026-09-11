<!-- capsule-v2 -->
# Network-error finish conversion — why must a provider's "network_error" finish reason become a thrown retryable failure?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100` (NEW in drift wave 4643e65→0352100, commits e0b9e68/40282c1/71d08e9 family). **Question:** When an OpenAI-compatible SDK reports a truncated stream as a normal step finish with `rawFinishReason: "network_error"`, how does the runtime turn it into something the retry policy can see?

## The finish-step interception
**Path/Symbol:** `packages/opencode/src/session/llm/ai-sdk.ts` `toLLMEvents` `"finish-step"` arm (:86-88); consumed by `retryable()` via `ProviderError.ResponseStreamError`.
**Signature:** `case "finish-step": if (event.rawFinishReason === "network_error") return Effect.fail(new ProviderError.ResponseStreamError("Provider finish_reason: network_error"))`.
**Data Shape:** converts a SUCCESS-shaped event (finish reason string) into a failed Effect carrying ResponseStreamError — which `parseStreamError`/`matchesRetryableMessage` classify as retryable, so the session retry Schedule re-streams instead of persisting a truncated assistant turn.

### Decisive source
```ts
// ai-sdk.ts:86-90 — BEFORE building the normal step-finish LLMEvent:
case "finish-step":
  if (event.rawFinishReason === "network_error")
    return Effect.fail(new ProviderError.ResponseStreamError("Provider finish_reason: network_error"))
  return Effect.sync(() => { ... })
```

Paired change in the classifier (`packages/opencode/src/provider/error.ts` :144-156): `parseStreamError` gained a terminal FALL-THROUGH so any unrecognized error body still yields `{type:"api_error", message: body?.error?.message ?? "Server error.", isRetryable: true}`. Previously unknown shapes returned `undefined` and were NOT retried; now they are retried by default.

And the loop-exit predicate (`packages/opencode/src/session/prompt.ts` :1113) treats finish reason `"unknown"` like `"tool-calls"` — do NOT end the turn when the finish reason is untrustworthy:
```ts
!["tool-calls", "unknown"].includes(lastAssistant.finish) &&
```
(the same predicate appears again at :1295 for the runner-side check).

**Flow:** provider transport dies mid-stream ⇒ SDK emits finish-step with rawFinishReason network_error ⇒ ai-sdk adapter FAILS the event instead of recording a step ⇒ SessionRetry.policy classifies ResponseStreamError as retryable (message contains no match needed — parseStreamError fall-through marks api_error isRetryable:true) ⇒ status set to "retry", stream restarted; if attempts exhaust, halt() records the error normally.
**Invariant:** A network-truncated response must never be persisted as a completed assistant turn — the conversion happens at the EVENT-ADAPTER layer (before persistence), not in UI code. The prompt-loop exit must treat `unknown` finish as non-terminal or the truncated turn ends the conversation silently.
**Probe:** direct pins (execute from repo root):
```bash
grep -n 'network_error' packages/opencode/src/session/llm/ai-sdk.ts
grep -n 'isRetryable: true' packages/opencode/src/provider/error.ts
```
expect hits at ai-sdk.ts :89/:90 and TWO in error.ts (:146 fall-through block + none other), plus direct test `packages/opencode/test/provider/error.test.ts` ("retries provider stream errors without a code") pinning xAI capacity + temporary-unavailable messages to `{type:"api_error", isRetryable:true}`.
**Coverage caveat:** the ai-sdk.ts conversion itself has no dedicated unit test upstream — behavior is pinned indirectly through retry.test.ts classification arms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "opencode", pattern: "rawFinishReason", limit: 4 });
// rank-1 = opencode.packages.opencode.src.session.llm.ai-sdk.toLLMEvents ai-sdk.ts :77-289 match :89 —
// the conversion arm itself; second hit is test/session/llm.test.ts (drives rawFinishReason arms)
// (BM25 "network_error" alone returns zero; this needle resolves the exact function)
```

## Verdict
Adopt fail-don't-persist on untrustworthy finish reasons and the retry-by-default unknown-error fall-through; adapt the exception type names; omit opencode's specific provider metadata plumbing.
