<!-- capsule-v2 -->
# Global cross-instance rate limiter — how do concurrent embedder instances share one 429 backoff state?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** When several embedder instances hit rate limits, how is backoff coordinated without a scheduler?

## static class state + mutex + consecutive-error exponential delay
**Path/Symbol:** `src/services/code-index/embedders/openai-compatible.ts` (:42-49 state; :397-475 helpers); openrouter.ts duplicates the SAME structure independently (:45-52, :332-411).
**Signature:** `waitForGlobalRateLimit(): Promise<void>` / `updateGlobalRateLimitState(error: HttpError)` / `getGlobalRateLimitDelay()`.
**Data Shape:** `{isRateLimited, rateLimitResetTime, consecutiveRateLimitErrors, lastRateLimitError, mutex}` — one static per CLASS (so per provider), never per instance.

### Decisive source
```ts
if (now - state.lastRateLimitError < 60000) { state.consecutiveRateLimitErrors++ } else { state.consecutiveRateLimitErrors = 1 }
const exponentialDelay = Math.min(5000 * Math.pow(2, state.consecutiveRateLimitErrors - 1), 300000)
state.rateLimitResetTime = now + exponentialDelay
```

**Flow:** before EVERY attempt `waitForGlobalRateLimit()` sleeps silently until resetTime (mutex released BEFORE the sleep so waiters don't serialize); a 429 bumps the consecutive counter (window = 60s since last 429) and pushes resetTime out 5s·2^(n−1) capped at 5min; retry delay = max(per-attempt backoff, global delay). State RESETS to not-limited once time passes.
**Invariant / trap:** openai-compatible and openrouter each hold their OWN static — a port that hoists "the" state into one shared module changes semantics (a Gemini limit would then stall OpenRouter traffic). The silent-wait design (no logging) is deliberate anti-log-flood.
**Probe:** `src/services/code-index/embedders/__tests__/openai-compatible-rate-limit.spec.ts` ("should apply global rate limiting across multiple batch requests" :64, "not exceed maximum delay of 5 minutes" :184, fake-timer based).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "globalRateLimitState waitForGlobalRateLimit consecutiveRateLimitErrors", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt static-per-provider rate-limit singletons with mutex-guarded read/update. Adapt base/cap constants. Omit the duplicated twin — factor it if you control both call sites.
