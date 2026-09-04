<!-- capsule-v2 -->
# Stats db seams — single-writer ingest, WAL, offsets, time-bucketed reads

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/stats/src/db.ts` + `usage-windows.ts`. **Question:** How does a local telemetry store stay consistent under one writer with many readers, resume ingestion after crashes, and serve honest time series?

## One handle, WAL, schema-capture-before-create
**Path/Symbol:** `packages/stats/src/db.ts:initDb` (108, async), `db` singleton (92), `closeDb` (1022), `getFileOffset` (442–451), `setFileOffset` (454–461), `insertMessageStats` (479), `getRecentRequests` (1062); backfill keys (`AGENT_TYPE_BACKFILL_KEY` etc., ~95–103).
**Signature:** `initDb(): Promise<Database>`; `getFileOffset(sessionFile): { offset, lastModified } | null`; `setFileOffset(sessionFile, offset, lastModified): void`; `getRecentRequests(limit = 100): MessageStats[]`.
**Data Shape:** SQLite tables `messages`/`user_messages`/`tool_calls` + per-file parse offsets; series points `{ t, value[, bucket] }`; `readUsageSnapshots → UsageSnapshotRow[] {provider, limitId, accountKey, window…}`.

### Decisive source
```ts
// Install the busy handler BEFORE any lock-taking statement. (issue #2421)
db.run("PRAGMA busy_timeout = 5000");
db.run("PRAGMA journal_mode = WAL");
// Whether `messages` predates this init — drives the one-time agent_type
// backfill below, so it must be sampled before CREATE TABLE adds the table.
const messagesTableExisted =
  db.prepare("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'messages'").get() !== undefined;
```

**Flow:** process-wide singleton (init returns the existing handle); WAL so reader queries never block the single writer; `busy_timeout` installed before any lock-taking statement keeps concurrent readers from failing on a locked writer. The pre-schema `messagesTableExisted` sample gates the one-time `agent_type` backfill on legacy DBs — re-running init is a no-op by construction.

**Invariant:** all migrations idempotent; offsets are per-session-file so sync resumes incrementally even after crashes.

## Read side: SQL-side bucketing, cutoff clipping, gap-honest series
**Path/Symbol:** `getTimeSeries` (756–791), `getModelTimeSeries` (793), `getProviderTimeSeries` (923), `getProviderHourlyBurn` (887), `getCostTimeSeries` (1096).
**Signature:** `getTimeSeries(hours = 24, cutoff?, bucketMs = 60*60*1000)`; `getModelTimeSeries(days = 14, cutoff?, bucketMs = 1d)`; `getCostTimeSeries(days = 90, cutoff?)`.

### Decisive source
```sql
SELECT (timestamp / ?) * ? as bucket,
       COUNT(*) as requests,
       SUM(CASE WHEN stop_reason = 'error' THEN 1 ELSE 0 END) as errors,
       SUM(total_tokens) as tokens, SUM(cost_total) as cost
FROM messages ${hasCutoff ? "WHERE timestamp >= ?" : ""}
GROUP BY bucket ORDER BY bucket ASC
```

**Flow:** series accept a `cutoff` UTC-ms to exclude later rows, then bucket by integer-division arithmetic INSIDE SQL — aggregation stays in the DB; buckets are computed as `(timestamp / bucketMs) * bucketMs`.

**Invariant:** the series never fabricate points for empty buckets — callers see gaps; granularity is chosen by the caller, never by the aggregation.

## Usage windows and fleet tokens
**Path/Symbol:** `usage-windows.ts:readUsageSnapshots` (72), `fetchUsageData` (125), `computeUsageWindowStats` (259), `sumFleetTokens` (177).

**Probe:** `test/db-range.test.ts` (offsets/buckets), `test/db-cost.test.ts` (cost series), `test/user-metrics.test.ts`, `test/provider-stats.test.ts`, `test/behavior-backfill.test.ts`, `test/gain-aggregator.test.ts`. Coverage caveat: tests excluded from graph index by design.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(initDb|getFileOffset|setFileOffset|insertMessageStats|getTimeSeries|getCostTimeSeries|readUsageSnapshots|sumFleetTokens)$", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt WAL + pre-lock busy_timeout ordering, schema-existence capture BEFORE create for gated one-time backfills, per-file incremental offsets, and SQL-side bucketing that leaves gaps honest; adapt table schemas, backfill keys, and window defaults to host telemetry needs; omit the agent-specific columns.
