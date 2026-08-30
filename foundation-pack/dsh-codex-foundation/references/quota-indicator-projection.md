<!-- capsule-v2 -->
# Quota indicator projection — how do you render a live quota chip from an untrusted status endpoint without ever showing wrong data?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how does a composer widget validate a whole auth-status payload, pick exactly the right rate-limit bucket for the current model, and poll — while hiding itself on anything unusable?

## Fail-soft whole-payload validation and exact bucket selection
**Path/Symbol:** `src/client/OpenAICodexQuotaIndicator.tsx:33-49 isWindow`, `:51-61 usageFromStatus`, `:63-68 weeklyQuotaOf`, `:70-76 isGptModel`, `:87-89 boundedQuotaPercent`, `:91-106 quotaProgressColor`, `:125-165 eligible-gated poll effect`, `:11-15 WEEK_SECONDS`/`SPARK_MODEL`/`SPARK_QUOTA_ID`.
**Signature:** `function usageFromStatus(value: unknown): OpenAICodexUsage | undefined`; `function weeklyQuotaOf(usage: OpenAICodexUsage, model: string | undefined): OpenAICodexRateLimitWindow | undefined`; `function quotaProgressColor(remainingPercent: number): { name: 'green'|'yellow'|'orange'|'red'; value: string }`.
**Data Shape:** input is whatever the auth-status route returned; output is either a fully validated `OpenAICodexUsage` or `undefined` — there is no partial acceptance.

### Decisive source
```ts
function isWindow(value: unknown): value is OpenAICodexRateLimitWindow {
  if (!isRecord(value)) return false
  const remainingPercent = value['remainingPercent']
  const windowSeconds = value['windowSeconds']
  const resetAt = value['resetAt']
  return typeof remainingPercent === 'number' && Number.isFinite(remainingPercent)
    && remainingPercent >= 0 && remainingPercent <= 100
    && typeof windowSeconds === 'number' && Number.isSafeInteger(windowSeconds) && windowSeconds > 0
    && (resetAt === undefined || (typeof resetAt === 'number'
      && Number.isSafeInteger(resetAt) && resetAt > 0
      && Number.isFinite(new Date(resetAt * 1_000).getTime())))
}

function usageFromStatus(value: unknown): OpenAICodexUsage | undefined {
  if (!isRecord(value) || value['status'] !== 'signed-in') return undefined
  const usage = value['usage']
  if (!isRecord(usage) || !Array.isArray(usage['rateLimits'])) return undefined
  for (const limit of usage['rateLimits']) {
    if (!isRecord(limit) || typeof limit['id'] !== 'string' || !Array.isArray(limit['windows'])) return undefined
    if (!limit['windows'].every(isWindow)) return undefined   // ONE bad window voids ALL
  }
  return usage as unknown as OpenAICodexUsage
}

function weeklyQuotaOf(usage, model) {
  const quotaId = model === SPARK_MODEL ? SPARK_QUOTA_ID : 'codex'  // EXACT match only
  return usage.rateLimits.find(limit => limit.id === quotaId)
    ?.windows.find(window => window.windowSeconds === WEEK_SECONDS)
}
```

**Flow:** directory snapshot (via `useSyncExternalStore`) → `isGptModel` gates eligibility (ready + provider `'openai-codex'` + lowercased model starts with `'gpt-'`) BEFORE any network call → effect fetches `OPENAI_CODEX_AUTH_STATUS_PATH` with same-origin credentials, validates through `usageFromStatus`, stores `{status:'ready', usage}` or `{status:'hidden'}` → renders null unless ready AND `weeklyQuotaOf` finds the 7-day window → width is `boundedQuotaPercent` (clamped 0-100), color thresholds ≥60 green / ≥40 yellow / ≥20 orange / else red, summary text lives in `aria-label` with hover/focus tooltip.
**Invariant:** hide-don't-guess: ineligible sessions, non-signed-in payloads, one malformed window anywhere, missing bucket for the exact model, failed requests, and empty rateLimits all render `null`; Spark quota (`codex_bengalfox`) is chosen only on exact model equality — `gpt-5.3-codex-spark-preview` stays on the plain `codex` bucket; polling runs every 60 s only while eligible, guarded by per-effect AbortController + `disposed` + `inFlight` flags, and unmount aborts the in-flight request.
**Probe:** `tests/openai-codex-quota-indicator.client.spec.tsx` (jsdom + testing-library): 11 cases pin eligibility gating with `expect(fetchMock).not.toHaveBeenCalled()` for non-GPT/wrong-provider, Spark exact-match selection plus no-fallback when its bucket is missing, the it.each color matrix (80→green, 50→yellow, 35→orange, 10→red), aria-label carrying percent+local reset time, hidden-on-failure, and `signal.aborted === true` after unmount.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: '^dsh-codex\\.src\\.client\\.OpenAICodexQuotaIndicator\\.(usageFromStatus|weeklyQuotaOf|quotaProgressColor|refresh|isWindow)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 6, has_more false (`isWindow` 33-49, `quotaProgressColor` 91-106, `refresh` 135-155, `usageFromStatus` 51-61, `weeklyQuotaOf` 63-68, plus `QuotaProgressColor` Type 85).

## Verdict
Adopt all-or-nothing payload validation, exact-id bucket selection with explicit no-fallback, clamped display arithmetic, and eligibility-gated polling that aborts on teardown. Adapt threshold values, bucket ids, and the directory/eligibility source to your host. Omit partial rendering of malformed usage data and any client-side retry storm — a failed poll simply hides the chip until the next interval. Coverage: source and spec are `no_recorded_issue` + `metadata_match`.
