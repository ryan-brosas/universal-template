<!-- capsule-v2 -->
# Backend health disable-latch — how do you stop polling a dead backend forever without lying about "connected", and survive page refreshes?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** Where should per-backend connectivity verdicts live so a flaky first probe doesn't disable anything, five real failures stop the polling across refreshes, and only a config fix re-arms it?

## Persisted verdict map + retry-inside-queryFn single-outcome rule
**Path/Symbol:** `src/api/backend-registry/health-store.ts` (`recordBackendFailure` :46–63, `recordBackendSuccess` :70–74, `commit` :19–23); `health-storage.ts` (`MAX_CONSECUTIVE_FAILURES=5` :10, `isValidEntry` :24–39, `truncateErrorMessage` :77–82); `src/hooks/query/use-backends-health.ts` (`probeBackendWithQuickRetry` :173–186, probe gates :239–286). Context re-arm: `active-backend-context.tsx` `updateBackend` :141–182.
**Signature:** `recordBackendFailure(id: string, error: unknown): void`; `useBackendsHealth(backends: Backend[], options?: { probeDisabledOnce?: boolean }): Record<string, BackendHealth>`.
**Data Shape:** `BackendHealthEntry { consecutiveFailures, lastError|null (≤500 chars), lastFailureAt|null, disabled }` in localStorage under `openhands-backend-health`; hook returns `{ isConnected: true|false|null, consecutiveFailures, lastError, disabled }` per id.

### Decisive source
```ts
// health-storage.ts — localStorage is user-writable; reject out-of-range counters.
//   a tampered `-1` would never reach the cap and would defeat the whole
//   disable mechanism, and a giant value would clutter the UI for no reason.
return (
  Number.isInteger(v.consecutiveFailures) &&
  (v.consecutiveFailures as number) >= 0 &&
  (v.consecutiveFailures as number) <= MAX_CONSECUTIVE_FAILURES && …
);
```
```ts
// use-backends-health.ts — retry INSIDE queryFn, not via React Query retry:
// the success/failure recording runs once per settled query, so a single
// logical probe still records exactly one outcome. Retrying at the query
// level would call recordBackendFailure on every internal attempt and reach
// the disabled cap several times too fast.
async function probeBackendWithQuickRetry(backend: Backend): Promise<true> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await probeBackend(backend);
    } catch (error) {
      if (attempt >= PROBE_RETRY_ATTEMPTS || !isRetryableProbeError(error)) {
        throw error;
      }
      await new Promise((resolve) => {
        setTimeout(resolve, PROBE_RETRY_DELAY_MS);
      });
    }
  }
}
```

**Flow:** per-backend `useQueries` keyed `[backend-health,id,kind,host,apiKey]` (config edits RE-KEY → instant refetch) → local probe = authenticated `getSettings()` then `/server_info` + version floor assert; cloud probe = `getCurrentCloudApiKey` (absorbs legacy-key 400) or org list for cookie auth, mapping 401→"Logged out" and CORS/network→"Cloud API key or network issue" instead of opaque browser errors → success DELETES the map entry (next tick marks healthy); failure increments capped at 5 and latches `disabled:true` → while disabled, `refetchInterval:false` and probes fire ONLY on `probeDisabledOnce` (Manage-Backends one-shot recheck with `refetchOnMount:"always"`) or the stale-CORS-error escape hatch → context `updateBackend` calls `resetBackendHealth(id)` ONLY when host/apiKey actually changed.
**Invariant:** One settled logical probe records EXACTLY ONE verdict outcome (definitive auth errors are never retried — they are decided responses). The latch is sticky BY DESIGN: it persists through refresh so the app never silently re-arms against a known-dead backend, and cosmetic edits (rename) must NOT clear it (test-pinned). Load-error ≠ binary-failure-style conflation: `lastError` stores the user-facing message truncated to 500 chars.
**Probe:** `__tests__/hooks/query/use-backends-health.test.tsx` (402 L) — transient-first-probe recovery records ZERO failures (:135–154), 401 not retried (:156–177), persisted-disabled skips probing after refresh (:302–334), `resetBackendHealth` re-arms (:336–369), `probeDisabledOnce` clears stale entry on success (:371–401); `__tests__/contexts/active-backend-context.test.tsx:288–326` pins rename-leaves-latched vs host-change-clears+`connectionRevision:1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "backend health probe failure disabled cap retry", limit: 10 });
```

## Verdict
Adopt the persisted-verdict-map shape, the 5-failure sticky latch cleared only by probe-driving edits, retry-inside-queryFn for exactly-once recording, and typed auth/network error mapping. Adapt probe endpoints and the CORS-escape recheck to your transport. Omit the cloud/cookie auth fork if single-backend. Coverage: no_recorded_issue on all cited paths at gen 2026-08-24T16:13:32Z; note two stale "10s" docstring spots in use-backends-health.ts — the constant is `REFRESH_INTERVAL_MS = 30000`.
