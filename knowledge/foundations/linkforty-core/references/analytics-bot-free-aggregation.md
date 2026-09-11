<!-- capsule-v2 -->
# Analytics bot-free aggregation — is_bot=false filter + COALESCE dimension buckets on every rollup

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** What must every click-analytics query carry so dashboards agree with each other?

## /api/analytics/overview + /api/analytics/links/:linkId
**Path/Symbol:** `src/routes/analytics.ts:analyticsRoutes` (:4-233); overview queries :16-97, per-link :157-209.
**Signature:** `GET /api/analytics/overview?userId&days=30` → `{ totalClicks, uniqueClicks, clicksByDate[], clicksByCountry[], clicksByDevice[], clicksByPlatform[], topLinks[] }`; unique = `COUNT(DISTINCT ip_address)`.
**Data Shape:** Every aggregate joins links (for user scoping) and filters `ce.is_bot = false` + time window; top-links uses LEFT JOIN with the filters in the JOIN clause (:89-91) so zero-click links still appear.

### Decisive source
```sql
-- analytics.ts:80-95 — the LEFT-JOIN-with-filters-in-join shape:
SELECT l.id, l.short_code, ..., COUNT(ce.id) as total_clicks,
       COUNT(DISTINCT ce.ip_address) as unique_clicks
FROM links l
LEFT JOIN click_events ce ON l.id = ce.link_id
  AND ce.clicked_at >= NOW() - INTERVAL '${days} days'
  AND ce.is_bot = false
${userFilterWhere}
GROUP BY l.id ORDER BY total_clicks DESC LIMIT 10;
-- dimensions: COALESCE(country_code,'Unknown'), device_type, platform
```

**Flow:** five overview queries (totals/date-bucket/country/device/platform/top-links) all repeat the identical filter trio → parseInt() over pg's string-typed counts at the boundary → per-link variant verifies existence (+optional ownership) first and throws 'Link not found' otherwise. Served by the partial index `idx_clicks_human_link_date (link_id, clicked_at DESC) WHERE is_bot = false` for the common shape.
**Invariant:** The is_bot filter is NOT optional on any consumer-facing count — ingestion persisted it precisely so reads stay consistent (bot-detection capsule); time-window filters belong in the JOIN condition for LEFT JOINs, not the WHERE, or zero-click rows vanish.
**Probe:** `bash -c "grep -c 'is_bot = false' src/routes/analytics.ts"` → 11 (6 overview + 5 link-level filter sites); direct tests: none target analytics.ts — recorded honest caveat (queries are thin SQL over tested write-side flags).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "analytics overview clicksByCountry total unique", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the invariant (every human-count carries the classification flag) and LEFT-JOIN-with-join-clause-filters shape; adapt dimensions/buckets; omit DISTINCT-ip uniqueness only if you have a better identity key — but keep one shared definition across ALL dashboard queries.
