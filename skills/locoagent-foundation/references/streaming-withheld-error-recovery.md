<!-- capsule-v2 -->
# Withheld-error streaming plane — why are prompt-too-long / media / max-output-tokens errors swallowed mid-stream, and what is the exact recovery ladder?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How can a turn survive API 413s, oversized-media rejections, and output-token caps WITHOUT surfacing a fatal error to SDK consumers?

## isWithheld* predicates + recovery ladder
**Path/Symbol:** `src/query.ts:isWithheldMaxOutputTokens` (:175-179), withholding block (:788-825), recovery ladder (:1062-1256), `MAX_OUTPUT_TOKENS_RECOVERY_LIMIT = 3` (:164), hoisted gate `mediaRecoveryEnabled` (:626-627).
**Signature:** `(msg: Message|StreamEvent|undefined) => msg is AssistantMessage` via `msg?.type === 'assistant' && msg.apiError === 'max_output_tokens'`; collapse/reactive twins delegate: `contextCollapse.isWithheldPromptTooLong(msg, isPromptTooLongMessage, querySource)`, `reactiveCompact.isWithheldPromptTooLong(msg)`, `reactiveCompact.isWithheldMediaSizeError(msg)`.
**Data Shape:** withheld messages are still PUSHED to local `assistantMessages` (:826-845) but NOT yielded — SDK callers (cowork/desktop) terminate the session on any `error` field, so yielding early leaks an intermediate error "the recovery loop keeps running but nobody is listening" (:167-174).

### Decisive source
```ts
let withheld = false
if (feature('CONTEXT_COLLAPSE')) {
  if (contextCollapse?.isWithheldPromptTooLong(message, isPromptTooLongMessage, querySource)) withheld = true }
if (reactiveCompact?.isWithheldPromptTooLong(message)) withheld = true
if (mediaRecoveryEnabled && reactiveCompact?.isWithheldMediaSizeError(message)) withheld = true
if (isWithheldMaxOutputTokens(message)) withheld = true
if (!withheld) { yield yieldMessage }
```

**Flow:** after streaming ends with no follow-up needed: (1) withheld 413 → try `contextCollapse.recoverFromOverflow` FIRST ("cheap, keeps granular context"), single-shot guarded by `state.transition?.reason !== 'collapse_drain_retry'`; committed>0 ⇒ continue with drained messages; (2) still 413 OR withheld-media → `reactiveCompact.tryReactiveCompact({hasAttempted: hasAttemptedReactiveCompact,...})`; success ⇒ rebuild post-compact messages, set guard true, continue as `reactive_compact_retry`; failure ⇒ surface withheld message + `executeStopFailureHooks` + return — explicitly NO fall-through to normal stop hooks ("Running stop hooks on prompt-too-long creates a death spiral: error → hook blocking → retry → error → … the hook injects more tokens each cycle" :1168-1175); (3) withheld max-output-tokens → escalating retry: if statsig cap enabled AND no explicit override AND no env var, retry SAME request at `ESCALATED_MAX_TOKENS` (64k vs 8k default) with no meta message, once per turn; else up to 3 multi-turn recoveries appending an `isMeta` user message "Output token limit hit. Resume directly — no apology, no recap… Pick up mid-thought" (:1224-1229); exhausted ⇒ finally yield the withheld error.
**Invariant:** (1) withholding and recovery MUST read the same gate value — hence hoisting before the stream; (2) either subsystem's withhold predicate is sufficient ("they're independent so turning one off doesn't break the other's recovery path" :792-794); (3) never let a blocked stop hook evaluate an API-error response (both 413-exhaustion and generic `lastMessage.isApiErrorMessage` exits bypass handleStopHooks :1258-1265); (4) media errors skip the collapse drain (collapse doesn't strip images); if oversized media sits in the preserved tail the retry will fail again — `hasAttemptedReactiveCompact` prevents the spiral and the error surfaces.
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `grep -n "isApiErrorMessage === 'max_output_tokens'\|apiError === 'max_output_tokens'" src/query.ts src/services/api/*.ts`; `sed -n '1223,1229p' src/query.ts` shows the verbatim recovery nudge text; `grep -n "death spiral" src/query.ts` pins both no-stop-hooks rationales (:1168-1175 area, :1258-1261).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "reactiveCompact isWithheldPromptTooLong", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the withhold→classify→ladder pattern and the death-spiral stops; adapt thresholds (64k escalate, 3 retries) and gate names; omit the statsig flag plumbing if you have none. Porting trap: yielding the withheld error immediately converts every recoverable overflow into a session-killing error for SDK consumers; the opposite trap is running stop hooks after exhaustion (token-injection loop).
