<!-- capsule-v2 -->
# Stats — honest usage windows, degraded gracefully

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/stats/src/usage-windows.ts`, `aggregator.ts`, `user-metrics.ts`. **Question:** How do telemetry surfaces stay truthful when the upstream is down, a fresh install has no history, or the schema predates the table?

## Usage windows that degrade instead of failing
**Path/Symbol:** `packages/stats/src/usage-windows.ts:readUsageSnapshots` (72–110), `sumFleetTokens` (177), `fetchUsageData` (125); `aggregator.ts` window composition; `user-metrics.ts:computeUserMessageMetrics` (627).
**Signature:** `readUsageSnapshots(sinceMs, dbPath = getAgentDbPath()): UsageSnapshotRow[]`.
**Data Shape:** `usage_history` rows (recorded_at, provider/account, limit_id, label, used_fraction, status, window_label); broker `ClientUsageClientSummary[]` per-client provider totals.

### Decisive source
```ts
export function readUsageSnapshots(sinceMs: number, dbPath = getAgentDbPath()): UsageSnapshotRow[] {
  let db: Database | null = null;
  try {
    db = new Database(dbPath, { readonly: true });
    db.run("PRAGMA busy_timeout = 5000");
    const rows = db.prepare(
      `SELECT recorded_at, provider, account_key, … FROM usage_history
       WHERE recorded_at >= ? ORDER BY recorded_at ASC`).all(sinceMs);
    return rows.map(row => ({ recordedAt: row.recorded_at, … }));  // snake_case → camelCase
  } catch (err) { logger.debug("usage_history unavailable"); return []; }
  finally { db?.close(); }
}
```

**Flow:** readonly open + busy_timeout → select rows since `sinceMs` ascending by time → map snake_case DB rows to camelCase TS; EVERY failure mode (fresh install, pre-usage schema, locked file) returns `[]` at debug level. The aggregator composes window stats on top: per-column sums, p50/p95/p99 latency, error counts, used_fraction vs limit. `computeUserMessageMetrics` is a pure per-message linter (yelling/profanity/anguish/negation) usable offline — no DB dependency.

**Invariant:** a missing or unreadable history is a DEGRADATION, never a throw; stats surfaces must still render past windows. Readers never open the agent DB read-write.

**Probe:** `packages/stats/test/db-range.test.ts` (getDashboardStats time range) is the canonical range-selection pin; `packages/stats/test/user-metrics.test.ts` pins the pure metric extraction; live stats tests remain bun-run green at `96f428097`. Coverage caveat: tests excluded from graph index by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(readUsageSnapshots|fetchUsageData|sumFleetTokens|aggregate|computeUserMessageMetrics)$", limit: 14, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.stats.src.usage-windows.readUsageSnapshots" });
```

## Verdict
Adopt readonly-open + busy_timeout readers that map failures to empty results, ascending-time snapshot reads feeding composed window aggregates, and pure offline user metrics; adapt the row schema and metric vocabulary to host; omit broker fleet-token plumbing unless multi-account reporting is needed.
