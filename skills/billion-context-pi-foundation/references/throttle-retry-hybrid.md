<!-- capsule-v2 -->
# Throttle-retry hybrid rewrite+kick machine — how do you auto-retry a provider rate limit without losing the task or looping forever?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** When a provider 429-throttles mid-task, what is the contract for classifying it, rewriting it into a retryable shape, budgeting retries across two channels, and resuming the interrupted work?

## Classification: a load-bearing string plus three regex guards
**Path/Symbol:** `src/throttle-retry.ts` whole (155L): `THROTTLE_RETRY_ERROR_MESSAGE` (:8), guards (:13-16), `isThrottleError` (:25-32), `isKickMessage` (:34-37), `resolveThrottleRetry` (:63-76), `throttleDelayMs` (:78-81), `ThrottleEpisode` (:91-144), `abortableSleep` (:146-154).
**Signature:** `isThrottleError(msg: ThrottleErrorProbe): boolean`; `ThrottleEpisode.onThrottleError(maxRetries): "rewrite" | "exhausted"`.
**Data Shape:** probe = `{ role, stopReason?, errorMessage?, content }`; haystack = `errorMessage + "\n" + extractText(content)` (relays put the upstream body in streamed content and leave errorMessage generic — errorMessage alone misses them).
### Decisive source
```ts
// throttle-retry.ts:8 — the rewritten error MUST survive pi's post-run classifier:
// contains "429" + "rate limit" so isRetryableAssistantError treats it as
// retryable; "rate limit" must NOT hit pi-ai's NON_OVERFLOW exclusion set
// (keeps it off the context-overflow/compaction path); matches no NON_RETRYABLE
// quota/billing pattern. Pinned by tests/throttle-retry.test.ts.
export const THROTTLE_RETRY_ERROR_MESSAGE = "429 rate limit: Too many tokens, please wait before trying again.";
// :28-31 — guard order IS the classifier: overflow first, quota second,
// only then accept "throttl" in errorMessage or the Bedrock phrase anywhere.
if (OVERFLOW_GUARD.test(haystack)) return false;
if (QUOTA_GUARD.test(haystack)) return false;
if (THROTTLE_NAME.test(msg.errorMessage ?? "")) return true;
return BEDROCK_THROTTLE_PHRASE.test(haystack);
```
**Flow:** `message_end` handler (`src/index.ts`:439-469): user message → `onUserMessage(isKickMessage(msg))` (any non-kick input resets the episode) → non-error assistant → `onProgress()` (full reset) → error that isn't throttle → `onNonThrottleError()` (clears candidate, keeps budget) → throttle → resolve config → `onThrottleError(maxRetries)` returns `"exhausted"` (surface the real error) or `"rewrite"` → return `{ message: { ...msg, errorMessage: THROTTLE_RETRY_ERROR_MESSAGE } }` so pi's NATIVE retry re-runs the turn within its own in-memory budget (~3). Channel 2: `agent_settled` fires after pi exhausts native retries; if `readyToKick(maxRetries)` still true, sleep `throttleDelayMs(kickNumber)` (60s base ×2^(n−1), capped 300s, exponential|fixed modes) via `abortableSleep`, then `pi.sendUserMessage(THROTTLE_KICK_TEXT)` — a sentinel-prefixed synthetic user message telling the model to resume exactly where it left off. Any `input` event with `source !== "extension"` calls `cancelSleep()` (AbortController), and `session_shutdown` → `throttleDrop(sid)` resets THEN deletes so a pending kick sleep can't outlive the session.
**Invariant:** (1) The rewritten string is load-bearing in THREE directions at once — retryable-for-pi, non-overflow-for-compaction, non-quota-for-fatal — change any word and the message lands on the wrong path. (2) Episode state is per-session keyed (`runtime.throttleFor(sid)` map) because concurrent sessions share one extension instance. (3) `abortableSleep` polls in ≤250ms slices checking `signal.aborted` FIRST — a plain `setTimeout` promise cannot be cancelled, which would send a kick after the user typed. (4) Exhaustion does NOT consume or reset the budget (`state.attempts >= maxRetries` just flips candidate off) so a later kick cycle can still use remaining attempts. (5) The kick re-checks `readyToKick` AFTER the sleep (:487) — state may have changed during 60–300s.
**Probe:** `cd /mnt/hdd/utopia/inspo/coding-agents/billion-context-pi && npx tsx --test tests/throttle-retry.test.ts` — 20/20 GREEN at pin incl. relay-shape/direct-Bedrock classification, overflow/quota rejection, the full "3 native + kick + 3 native + kick + exhaustion" timeline, reset semantics, and delay math.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "ThrottleEpisode isThrottleError throttleDelayMs abortableSleep", limit: 10 });
```

## Verdict
Adopt the two-channel design (native rewrite for fast probes, self-managed kick for long waits), the triple-guard classifier order, the load-bearing error string discipline (document WHY each phrase is required next to the literal), per-session episode maps with drop-on-shutdown, and abortable sleep with post-sleep re-check. Adapt host hook names (`message_end`, `agent_settled`, `input`, `sendUserMessage`) and the native-retry trigger mechanism to your platform. Omit nothing — every branch here was added because a naive port loops forever or resumes wrong.
