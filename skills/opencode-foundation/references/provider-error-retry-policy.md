<!-- capsule-v2 -->
# Provider-error retry policy — which LLM failures does opencode retry, and how long does it wait?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100` (pass-5 refresh); Codebase Memory `opencode`. **Question:** How are retryable provider failures classified, and what backoff governs the wait between attempts?

## Retryable classification ladder
**Path/Symbol:** `packages/opencode/src/session/retry.ts` (:26-31 constants; `RETRYABLE_MESSAGE_PATTERNS` :33-40; `delay` :46–77; `retryable` :84–154; `policy` :182–206).
**Signature:** `retryable(error: Err, provider: string) → {message, action?} | undefined` / `delay(attempt, error?, random?) → ms` / `policy({provider, parse, set}) → Schedule`.
**Data Shape:** `Err` is a NamedError toObject; only `SessionV1.ContextOverflowError` and `SessionV1.APIError` get special arms. APIError carries `{statusCode, isRetryable, message, responseBody, responseHeaders}`. Return shape feeds UI: plain `{message}` for generic retries, full `action` envelope (`reason/title/message/label/link`) for Go upsell limits.

### Decisive source
```ts
// retry.ts:85-97 — overflow NEVER retries; 5xx overrides the SDK's own retryable flag
if (SessionV1.ContextOverflowError.isInstance(error)) return undefined
if (SessionV1.APIError.isInstance(error)) {
  const status = error.data.statusCode
  if (
    !error.data.isRetryable &&
    !(status !== undefined && status >= 500) &&
    !matchesRetryableMessage(error.data.message) &&
    !matchesRetryableMessage(error.data.responseBody)
  )
    return undefined
// retry.ts:33-40 — message/body heuristics catch SDKs that misclassify
const RETRYABLE_MESSAGE_PATTERNS = [
  /429|500|502|503|504|524/i,
  /rate increased too quickly|rate limit|rate-limit|rate_limit|too many requests/i,
  /overloaded|service unavailable|service_unavailable|...|provider returned error|provider_returned_error|provider-returned-error/i,
  /terminated|fetch failed|failed to fetch|network[-_\s]error|upstream connect|connection error|connection refused|connection lost|socket connection was closed|socket hang up|reset before headers|getaddrinfo|enotfound|eai_again|econnrefused|econnreset|etimedout/i,
  /^timeout$|\b(?:request|response|connection|network|stream|read) (?:timeout|timed out|time out)\b/i,
  /try your request again|retry your request|resource exhausted|resource_exhausted/i,
  /\btry again (?:later|in\b)|\b(?:currently|temporarily) at capacity\b/i,   // NEW @0352100
]
```

PASS-5 DRIFT NOTE (@0352100): two pattern-list changes — `network error` became `network[-_\s]error` (matches "network_error"/"network-error" snake/kebab forms) and a SEVENTH pattern was added matching xAI/OpenAI capacity phrasing ("try again later/in…", "currently/temporarily at capacity"). Also NEW: `parseStreamError` (provider/error.ts :144-156) gained a retryable api_error FALL-THROUGH for previously-unrecognized bodies — unknown error shapes are now retried by default instead of dropped; and finish-step events with `rawFinishReason === "network_error"` are converted to ResponseStreamError at the ai-sdk adapter so truncated streams enter THIS policy (see network-error-finish-conversion.md).

**Flow:** Order of precedence: (1) ContextOverflowError ⇒ no retry; (2) APIError with `FreeUsageLimitError` in body ⇒ upsell action (`reason:"free_tier_limit"`, link opencode.ai/go); (3) body containing `GoUsageLimitError` ⇒ workspace-limit action with humanized reset countdown parsed from `metadata.workspace`/`limitName` + `retry-after` header (days/hours/minutes grammar :116-127); (4) other APIErrors pass the four-way gate (isRetryable ∨ status≥500 ∨ message-match ∨ body-match); (5) non-APIError records fall through lowercase substring checks (`too_many_requests`, `exhausted`, `unavailable`) then the pattern list.
**Invariant:** Status ≥500 retries EVEN WHEN the provider SDK marked the error non-retryable — the comment pins this as deliberate (:89-90). ContextOverflow must stay non-retryable or compaction-driven recovery loops forever. The two Go-limit bodies are checked by SUBSTRING on raw responseBody before any JSON parse, so they win over generic classification regardless of wrapper shape.
**Probe:** `packages/opencode/test/session/retry.test.ts` — ":260 does not retry context overflow errors", ":269 retries 500 errors even when isRetryable is false", ":282 retries 502 bad gateway errors", ":294 retries 503 service unavailable errors"; delay matrix at :35-150 ("caps delay at 30 seconds when headers missing" :36, "uses retry-after values even when exceeding 10 minutes with headers" :84, "caps oversized header delays to the runtime timer limit" :92).

## Backoff arithmetic
**Path/Symbol:** same file, `delay` :46–77 + `exponential` :79–82.
**Data Shape:** Constants :26-31 — initial 2_000ms, factor 2, jitter ×0.25, header-less cap 30_000ms, absolute cap `2_147_483_647` (32-bit setTimeout ceiling), max attempts 5.

### Decisive source
```ts
// retry.ts:46-76 — header hints bypass the 30s cap entirely; only their own cap applies
if (headers["retry-after-ms"]) return cap(parseFloat(retryAfterMs))
if (headers["retry-after"]) {
  const secs = Number.parseFloat(retryAfter)
  if (!Number.isNaN(secs)) return cap(Math.ceil(secs * 1000))
  const parsed = Date.parse(retryAfter) - Date.now()          // HTTP-date form
  if (!Number.isNaN(parsed) && parsed > 0) return cap(Math.ceil(parsed))
}
return cap(exponential(attempt, random))
// ...and WITHOUT any headers:
return cap(Math.min(exponential(attempt, random), RETRY_MAX_DELAY_NO_HEADERS))
// retry.ts:79-82 — base·2^(attempt-1) plus up to +25% jitter, ceil'd
const base = RETRY_INITIAL_DELAY * Math.pow(RETRY_BACKOFF_FACTOR, attempt - 1)
return Math.ceil(base + base * RETRY_JITTER_FACTOR * random)
```

**Flow:** `policy()` wraps this into an Effect `Schedule.fromStepWithMetadata`: each step parses the failure via injected `parse`, asks `retryable`, stops with `Cause.done(meta.attempt)` when exhausted (attempt > 5) or unclassified, else reports `{attempt, message, action?, next}` through `set` so the TUI can render "retrying in Ns" and waits `Duration.millis(wait)` (:187-205).
**Invariant:** Header-provided delays (`retry-after-ms`, seconds-form AND HTTP-date-form `retry-after`) are honored up to the 32-bit timer cap — never clamped to 30s — because the provider told us exactly when capacity returns. Only the blind exponential path is capped at 30s. Jitter is ADDITIVE (+0–25%), not multiplicative range.
**Probe:** direct constants pin:
```bash
grep -n 'RETRY_INITIAL_DELAY\|RETRY_MAX_DELAY_NO_HEADERS\|RETRY_MAX_RETRIES\|JITTER' packages/opencode/src/session/retry.ts
```
expect :26,:27,:28,:29,:30,:31 all present.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "retryable delay policy", limit: 5 });
// resolves opencode.packages.opencode.src.session.retry.delay (retry.ts:46-77) and
// opencode.packages.opencode.src.session.retry.retryable (retry.ts:84-154)
```

## Verdict
Adopt the classification precedence (overflow-no-retry → Go-limit actions → 5xx-forces-retryable → pattern heuristics) and the dual-cap delay arithmetic verbatim; adapt the Schedule wiring and error schema to host; omit Go product copy.
