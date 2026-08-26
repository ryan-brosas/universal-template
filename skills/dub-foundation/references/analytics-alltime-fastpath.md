<!-- capsule-v2 -->
# Analytics all-time fast path — when can a dashboard count skip ClickHouse entirely?

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** Which exact query shape may read denormalized MySQL counters instead of the event warehouse, and why is that safe?

## Guarded MySQL aggregate bypass in getAnalytics
**Path/Symbol:** `apps/web/lib/analytics/get-analytics.ts:getAnalytics` (:54-78; guard clause starts :54, aggregate columns :65-70, execute :72-75).
**Signature:** `getAnalytics(params: AnalyticsFilters): Promise<CountObject | number | Row[]>`.
**Data Shape:** fires only when ALL hold: parsed linkId present, `groupBy === "count"`, `interval === "all"`, no custom start/end, and every `DIMENSIONAL_ANALYTICS_FILTERS` entry is unset (:60). Returns `analyticsResponse["count"].parse(row)`.

### Decisive source
```ts
if (
  normalizedLinkId &&
  groupBy === "count" &&
  interval === "all" &&
  !start &&
  !end &&
  DIMENSIONAL_ANALYTICS_FILTERS.every(
    (filter) => !params[filter as keyof AnalyticsFilters],
  )
) {
  const linkIdPlaceholders = normalizedLinkId.values.map(() => "?").join(",");
  const aggregateColumns =
    event === "composite"
      ? `SUM(clicks) as clicks, SUM(leads) as leads, SUM(sales) as sales, SUM(saleAmount) as saleAmount`
      : event === "sales"
        ? `SUM(sales) as sales, SUM(saleAmount) as saleAmount`
        : `SUM(${event}) as ${event}`;

  const response = await conn.execute(
    `SELECT ${aggregateColumns} FROM Link WHERE id IN (${linkIdPlaceholders}) AND projectId = ?`,
    [...normalizedLinkId.values, workspaceId],
  );

  return analyticsResponse["count"].parse(response.rows[0]);
}
```
(get-analytics.ts :54-77)

**Flow:** linkId normalized to ParsedFilter → five-clause guard → placeholder-bound `IN (...)` + `projectId = ?` tenancy → SUM columns chosen by event (composite = all four metrics) → zod-whitelisted row returned. Everything else falls through to the Tinybird funnel.
**Invariant:** correctness rests on Link's denormalized counters being live-synced by click ingestion; adding any dimensional filter or custom window to this path would silently serve stale aggregates — the guard is the contract, not an optimization hint.

**Probe:** executed at pin: `grep -n 'DIMENSIONAL_ANALYTICS_FILTERS.every' apps/web/lib/analytics/get-analytics.ts` → :60; `grep -n 'SUM(clicks) as clicks' ...` → :67; `grep -n 'projectId = ?' ...` → :73. Direct test `tests/analytics/get-analytics.test.ts` is CI-gated integration (runner offline-blocked; anchor :8 `describe.runIf(env.CI)`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", name_pattern: "^getAnalytics$", limit: 5, fields: ["signature"] });
```
(observed rank-1: `getAnalytics Function 27-401 "(params: AnalyticsFilters)"`.)

## Verdict
Adopt the five-clause guard + placeholder-bound tenancy + composite column fold. Adapt the SQL client (Planetscale `conn.execute`). Omit dub's specific metric column names.
