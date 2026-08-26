<!-- capsule-v2 -->
|# MetaSync dual-method body — 'all' sentinel, socket-excluded broadcast, diff-returns-changeset

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What do the sync and diff method BODIES actually do differently — beyond the JobsMap routing?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/meta-sync/meta-sync.processor.ts:job` (19–68), `metaDiffJob` (70–101); routing entries `jobs-map.service.ts:57-63`.

**Signature:** `job(job)` mutates via `metaDiffsService.metaDiffSync | baseMetaDiffSync`; `metaDiffJob(job)` reads via `metaDiff | baseMetaDiff` and RETURNS the changeset as the job value.

**Data Shape:** payload `{context, sourceId, user, req}`; `sourceId === 'all'` is the whole-base sentinel choosing base-wide vs per-source service calls. Sync broadcasts AFTER mutation; diff returns data.

### Decisive source
```ts
if (info.sourceId === 'all') {
  await this.metaDiffsService.metaDiffSync(context, { baseId, logger: logBasic, req });
} else {
  await this.metaDiffsService.baseMetaDiffSync(context, { baseId, sourceId: info.sourceId, ... });
}
NocoSocket.broadcastEvent(context,
  { event: EventType.META_EVENT, payload: { action: 'source_meta_sync',
      payload: { base_id, source_id: info.sourceId } } },
  context.socket_id);            // exclude the triggering client's own socket
```

**Flow:** SYNC → 'all'-branched reconciliation with streamed progress → broadcast META_EVENT minus the initiator's socket (they already know) → done. DIFF → same branch shape over read-only service calls → return changeset (flows back through /jobs/listen to the requester).

**Invariant:** (1) The literal `'all'` string is the fan-out-scope API — not null, not an array; keep the exact comparison when porting. (2) Broadcast rides only the MUTATING path and always excludes `context.socket_id` (complete-then-broadcast at job layer). (3) Diff's value is that it RETURNS: job results are the read-back channel, no separate fetch API. (4) Shared logBasic gives preview and apply identical progress parity.

**Probe:** no unit test upstream. Source-grounded probe: whole file cited above (101 L), pairing capsules metasync-diff-split.md + meta-sync-broadcast.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "metaDiffSync baseMetaDiffSync metaDiff NocoSocket broadcastEvent", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the 'all' sentinel, mutate-then-broadcast-with-exclusion, return-the-changeset diff; adapt event names; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
