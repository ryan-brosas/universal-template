<!-- capsule-v2 -->
# remote history cursor pagination — how do you page a live event log backwards without missing new events?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** A remote session store serves an append-only event stream — what request shapes fetch "latest page" and "older pages" so the UI can scroll history while new events keep arriving?

## sessionHistory.ts: anchor_to_latest + before_id cursor pair over an auth-reused context
**Path/Symbol:** `src/assistant/sessionHistory.ts`:`HISTORY_PAGE_SIZE` `:7`, `HistoryPage` `:9-16`, `createHistoryAuthCtx` `:31-43`, `fetchPage` `:45-67`, `fetchLatestEvents` `:73-78`, `fetchOlderEvents` `:81-87`.
**Signature:** `createHistoryAuthCtx(sessionId: string): Promise<HistoryAuthCtx>`; `fetchLatestEvents(ctx, limit = 100): Promise<HistoryPage | null>`; `fetchOlderEvents(ctx, beforeId: string, limit = 100): Promise<HistoryPage | null>`.
**Data Shape:** `HistoryPage = { events: SDKMessage[] (chronological), firstId: string | null, hasMore: boolean }` — `firstId` doubles as the NEXT-OLDER cursor. Server shape `{ data, has_more, first_id, last_id }`. Headers carry `anthropic-beta: ccr-byoc-2025-07-29` + `x-organization-uuid`.

### Decisive source
```ts
// :45-67 — every failure mode collapses to null
async function fetchPage(ctx, params, label): Promise<HistoryPage | null> {
  const resp = await axios.get(ctx.baseUrl, {
    headers: ctx.headers,
    params,
    timeout: 15000,
    validateStatus: () => true,          // never throw on HTTP status
  }).catch(() => null)                   // network errors → null too
  if (!resp || resp.status !== 200) {
    logForDebugging(`[${label}] HTTP ${resp?.status ?? 'error'}`)
    return null
  }
  return {
    events: Array.isArray(resp.data.data) ? resp.data.data : [],  // shape guard
    firstId: resp.data.first_id,
    hasMore: resp.data.has_more,
  }
}
// :73-78 newest page; :86 older page
return fetchPage(ctx, { limit, anchor_to_latest: true }, 'fetchLatestEvents')
return fetchPage(ctx, { limit, before_id: beforeId }, 'fetchOlderEvents')
```

**Flow:** open history → ONE `createHistoryAuthCtx` (OAuth token + org UUID + beta header resolved once, reused across all pages) → latest via `anchor_to_latest=true` (last N events, chronological) → user scrolls up → pass page's `firstId` as `before_id` for the next-older page → repeat while `hasMore`.
**Invariant:** The newest page must be requested with a MOVING anchor (anchor_to_latest), not a fixed offset — the stream is append-only, so offset windows shift under you; older pages then use the STABLE event-ID cursor (`before_id`) which is immune to concurrent appends. Auth context is prepared once and reused because token prep is the expensive part, not paging. Every failure (network throw, non-200, malformed body) normalizes to `null` so callers render "history unavailable" instead of crashing; the array-shape guard keeps a 200-with-garbage body from becoming a TypeError.
**Probe:** Deterministic pins: `grep -n 'HISTORY_PAGE_SIZE = ' src/assistant/sessionHistory.ts` → `7:` (=100); `grep -n 'ccr-byoc' src/assistant/sessionHistory.ts` → `39:`; `grep -n 'validateStatus: () => true' src/assistant/sessionHistory.ts` → `55:`; `grep -n 'anchor_to_latest\|before_id' src/assistant/sessionHistory.ts | wc -l` → `4` (:12 comment + :70 comment + :77 + :86).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "sessionHistory fetchOlderEvents before_id anchor_to_latest", limit: 10 });
```

## Verdict
Adopt ID-cursor backward paging with a moving-anchor newest page for append-only logs. Adapt endpoint/beta header to your backend; keep the null-normalizing fetch wrapper and one-time auth ctx. Omit nothing else — it's already minimal.
