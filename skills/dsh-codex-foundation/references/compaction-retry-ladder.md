<!-- capsule-v2 -->
# Abort-aware compaction retry ladder — honor server timing hints, cap attempts, and never retry after abort

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should a request retry ladder combine server Retry-After hints, exponential fallback, attempt caps, and abort responsiveness?

## retryDelayMs / retryableStatus / waitForRetry / requestSignal / MAX_NATIVE_COMPACTION_RETRIES
**Path/Symbol:** src/responses.ts:200-246 (delay 200-214, status 216-218, wait 220-240, signal 242-246); cap constant 38 and clamp/use at 472-497.
**Signature:** retryDelayMs(response: Response, attempt: number): number; retryableStatus(status: number): boolean; waitForRetry(delay: number, signal?: AbortSignal): Promise<void>; requestSignal(signal: AbortSignal | undefined, timeoutMs: number | undefined): AbortSignal | undefined.
**Data Shape:** Retryable statuses are exactly 429, 500, 502, 503, 504. Delay precedence: retry-after-ms (finite >= 0) → retry-after seconds → retry-after HTTP-date (date - now) → min(4000, 500 * 2**attempt). MAX_NATIVE_COMPACTION_RETRIES = 2; caller maxRetries is clamped into [0, 2].

### Decisive source
~~~ts
async function waitForRetry(delay: number, signal?: AbortSignal): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    if (signal === undefined) { setTimeout(resolve, delay); return }
    if (signal.aborted) { reject(signal.reason); return }
    const onAbort = (): void => { clearTimeout(timeout); reject(signal.reason) }
    const timeout = setTimeout(() => { signal.removeEventListener('abort', onAbort); resolve() }, delay)
    signal.addEventListener('abort', onAbort, { once: true })
  })
}

function requestSignal(signal: AbortSignal | undefined, timeoutMs: number | undefined): AbortSignal | undefined {
  if (timeoutMs === undefined || timeoutMs <= 0) return signal
  const timeout = AbortSignal.timeout(timeoutMs)
  return signal === undefined ? timeout : AbortSignal.any([signal, timeout])
}

// dispatch loop (474-497): network error rethrown when aborted or final attempt;
// non-retryable HTTP status or final attempt rethrows with body detail truncated to 1000 chars;
// otherwise waitForRetry(retryDelayMs(response, attempt), options?.signal)
~~~

**Flow:** attempt fetch under combined caller+timeout signal → transport error: rethrow if aborted or attempts exhausted, else wait and continue → onResponse hook observes every status+headers → non-ok: build bounded-detail error, rethrow unless retryableStatus and attempts remain → delay from server hint else exponential backoff capped at 4s.
**Invariant:** abort rejects the pending wait immediately with signal.reason and removes its listener (no leak, no post-abort sleep); per-request timeout composes via AbortSignal.any rather than replacing the caller signal; the effective retry count can never exceed 2 regardless of caller input; every terminal error carries at most 1000 chars of response body; lastError is always thrown if the loop exits without success.
**Probe:** tests/codex-compaction.spec.ts:324-387 — native endpoint answers HTTP 400 (non-retryable) once and the run falls straight back to the standard stream in one extra request; executed via pnpm test -- tests/codex-compaction.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.responses\\.(retryDelayMs|retryableStatus|waitForRetry|requestSignal)', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt hint-first delay resolution, the small hard cap on retries, abort-racing sleeps, and bounded error bodies for any provider loop. Adapt status set and header names to the target API. Omit Codex-specific routing headers. Coverage no_recorded_issue + metadata_match for src/responses.ts and tests/codex-compaction.spec.ts; timer/abort races are source-confirmed — the suite pins the non-retryable fast-fail path only.
