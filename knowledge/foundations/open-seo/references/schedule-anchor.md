<!-- capsule-v2 -->
# Schedule anchor — how do you compute next-run times so delayed runs never drift the schedule?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** How is the next check time derived for daily/weekly/monthly configs, and what does the anchor prevent?

## Drift-free anchor advancement
**Path/Symbol:** `src/shared/rank-tracking.ts:computeNextCheckAt` (:178-223), `endOfMonthWithTime` (:151-166).
**Signature:** `function computeNextCheckAt(interval: "daily"|"weekly"|"monthly", previousNextCheckAt?: string | null): string` (ISO timestamp).
**Data Shape:** Daily = +1 day, weekly = +7 days; monthly = end-of-month at the anchor's wall-clock time (UTC); first-ever schedule picks a random hour 04–09 UTC + random minute as jitter.

### Decisive source
```ts
/**
 * Compute the next check time for a scheduled config.
 *
 * If `previousNextCheckAt` is provided, advances from that anchor by the
 * interval until the result is in the future. This prevents schedule drift
 * when runs are delayed (e.g., a weekly config due Monday that fires on
 * Wednesday will still schedule the next check for the following Monday).
 */
if (previousNextCheckAt) {
  const anchor = new Date(previousNextCheckAt).getTime();
  const intervalMs = daysAhead * 86_400_000;
  const steps = Math.floor(Math.max(0, now - anchor) / intervalMs) + 1;
  return new Date(anchor + steps * intervalMs).toISOString();
}
```

**Flow:** With an anchor: step forward in whole intervals from the ANCHOR until strictly future (`steps = floor(max(0, now-anchor)/interval)+1`) → monthly keeps the anchor's time-of-day across `endOfMonthWithTime(anchor, offset)` while walking month offsets until future. Without an anchor (first schedule): now+interval with random 04–09 UTC jitter (monthly: end of current month at that jitter time, pushed a month out if past). Callers pass the OBSERVED row value as anchor — the cron claims the slot by CAS on that observed value before starting work.
**Invariant:** Always advance from the previous anchor, never from `now` — advancing from now compounds every outage/delay into permanent drift and herd-syncs configs after incidents. Monthly must preserve the anchor's clock time so end-of-month checks stay consistent.
**Probe:** `src/shared/rank-tracking.test.ts` (anchor-advancement vs delay cases) — locate via `grep -rn "computeNextCheckAt" src/shared/*.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "computeNextCheckAt previousNextCheckAt anchor drift", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt anchor-based advancement for ANY recurring job stored in a DB row. Adapt interval set and jitter window to your product. Omit the monthly end-of-month special case if you only support fixed-interval schedules.
