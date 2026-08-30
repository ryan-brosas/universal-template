<!-- capsule-v2 -->
# Schema-maintenance scheduler — how does teable coalesce repeated schema changes into one rebuild task without losing the latest reason?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Every schema change on a table with a managed search vector wants a rebuild. How do you serialize that under an advisory lock and coalesce bursts into a single queued task (updating its payload) instead of piling up N tasks?

## Advisory-xact-lock + coalesce-or-insert rebuild task
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/searchVectorMaintenance.ts` — `PostgresTableSearchVectorSchemaMaintenanceScheduler.schedule` (27–130).
**Signature:** `schedule(ctx, input: {table, reason}): Promise<Result<TableSearchVectorSchemaMaintenanceSchedule | undefined, DomainError>>`.
**Data Shape:** returns `{tableId, taskId, status:'queued'|'coalesced'}` or `undefined` when the table has no active search-vector config.

### Decisive source
```ts
const scheduled = await this.metaDb.transaction().execute(async (trx) => {
  await sql`SELECT pg_advisory_xact_lock(hashtext('teable.table_query_ops.search_vector_maintenance'), hashtext(${tableId}::text))`.execute(trx);
  const config = await sql`SELECT id FROM table_query_search_vector_config
    WHERE table_id=${tableId} AND status IN ('ready','stale','rebuild_pending')
    ORDER BY last_modified_time DESC NULLS LAST, created_time DESC LIMIT 1`.execute(trx);
  if (!config.rows[0]) return undefined;                       // no active vector → nothing to rebuild
  await sql`UPDATE table_query_search_vector_config SET status='rebuild_pending',
      last_inspection=jsonb_build_object('state','rebuild_pending','reason',${input.reason}::text),
      last_modified_time=now() WHERE id=${activeConfig.id}`.execute(trx);
  const queued = await sql`SELECT id FROM table_query_remediation_task
    WHERE table_id=${tableId} AND kind IN ('rebuild_search_access_path','rebuild_search_vector')
      AND status='queued' AND payload->>'trigger'='schema_change'
    ORDER BY created_time DESC LIMIT 1`.execute(trx);
  if (queued.rows[0]) {                                        // COALESCE: refresh the reason, don't duplicate
    await sql`UPDATE table_query_remediation_task SET payload=${JSON.stringify({trigger:'schema_change', reason:input.reason})}::jsonb, last_modified_time=now() WHERE id=${queued.rows[0].id}`.execute(trx);
    return { tableId, taskId: queued.rows[0].id, status: 'coalesced' };
  }
  const task = TableQueryRemediationTask.createQueued({ tableId, baseId, kind:'rebuild_search_access_path',
    payload:{trigger:'schema_change', reason:input.reason}, now:new Date() })._unsafeUnwrap();
  await sql`INSERT INTO table_query_remediation_task (id,base_id,table_id,kind,status,payload,attempts,max_attempts,created_time) VALUES (...)` .execute(trx);
  return { tableId, taskId: snapshot.id, status: 'queued' };
});
```

**Flow:** within a transaction, take a per-table advisory xact lock → find the active search-vector config (ready/stale/rebuild_pending) → if none, return undefined → flip the config to `rebuild_pending` with the reason stamped into `last_inspection` → look for an existing `queued` schema-change rebuild task → if found, COALESCE by updating its payload to the newest reason (status `coalesced`); else create a fresh `rebuild_search_access_path` task (status `queued`).
**Invariant:** the advisory xact lock serializes concurrent schema changes for the same table so coalescing is race-free; an existing queued task is updated, never duplicated; the config is always flipped to `rebuild_pending` even when coalescing, so the status reader reports a pending rebuild.
**Probe:** exercised through `searchVector.lifecycle.db.spec.ts` and the schema-change maintenance path; no dedicated unit spec for the scheduler (DB-backed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableSearchVectorSchemaMaintenanceScheduler schedule pg_advisory_xact_lock coalesced", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the advisory-xact-lock serialization + coalesce-or-insert rebuild task with reason-stamped config flip; adapt lock-key namespace and task kind vocab to host; omit the search-vector specifics if the host has no managed search index. Coverage: fully indexed.
