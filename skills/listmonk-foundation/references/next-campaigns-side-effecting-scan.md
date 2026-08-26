<!-- capsule-v2 -->
# next-campaigns-side-effecting-scan — How does the dispatcher discover due campaigns without double-counting sends across scans?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** Why does the "get next campaigns" query UPDATE rows, and what must a porter preserve?

## Scan-with-side-effects CTE
**Path/Symbol:** `queries/campaigns.sql -- name: next-campaigns` (:174-226); Go caller pair `internal/manager/manager.go:getCurrentCampaigns` (:588-604) + `scanCampaigns` (:449-487); batch fetcher `-- name: next-campaign-subscribers` (:318-372).
**Signature:** `NextCampaigns(currentIDs []int64, sentCounts []int64)` (Store interface, `internal/manager/manager.go:44-54`).
**Data Shape:** `$1` = running campaign IDs (already held in pipes), `$2` = their pending sent counts; returns campaigns + aggregated media IDs.

### Decisive source
```sql
updateCounts AS (
	WITH uc (campaign_id, sent_count) AS (SELECT * FROM unnest($1::INT[], $2::INT[]))
	UPDATE campaigns SET sent = sent + uc.sent_count FROM uc WHERE campaigns.id = uc.campaign_id
),
u AS (
	UPDATE campaigns AS ca SET to_send = co.to_send,
		status = (CASE WHEN status != 'running' THEN 'running' ELSE status END),
		max_subscriber_id = co.max_subscriber_id,
		started_at=(CASE WHEN ca.started_at IS NULL THEN NOW() ELSE ca.started_at END)
	FROM (SELECT * FROM counts) co WHERE ca.id = co.campaign_id
)
```

**Flow:** every tick: flush accumulated per-pipe sent counters into the cumulative DB column (`sent += delta`; in-memory counter reset to 0 after read — see getCurrentCampaigns' deliberate `p.sent.Store(0)`) → recompute `to_send` as COUNT(DISTINCT subscriber) over optin-status-aware joins → claim scheduled campaigns whose time has come → compute `max_subscriber_id` upper bound → return newly-discovered campaigns for pipe creation. Subscriber batches then walk `id > last_subscriber_id AND id <= max_subscriber_id`, each fetch advancing the checkpoint inside its own CTE.
**Invariant:** Discovery and accounting live in ONE statement because both sides race otherwise: counting subscribers separately from claiming lets a concurrent subscription change skew `to_send`. The static `sl.list_id = ANY($5::INT[])` bind in next-campaign-subscribers is a documented planner workaround (comment cites ~15s → milliseconds on 70M-row subscriber_lists) — dynamic joins regress catastrophically; keep list IDs literal-bound.
**Probe:** `bash -c "cd <repo> && grep -c 'UPDATE campaigns' queries/campaigns.sql"` → 7 UPDATE sites across the file; `grep -c 'p.sent.Store(0)' internal/manager/manager.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "next-campaigns scanCampaigns", limit: 10 });
```
## Verdict
Adopt checkpointed batch fetching with an upper bound snapshot and delta-flushed counters. Adapt the CTE shape to your DB's upsert idioms. Omit the Postgres-specific planner workaround unless you also use PG with partitioned subscriber joins.
