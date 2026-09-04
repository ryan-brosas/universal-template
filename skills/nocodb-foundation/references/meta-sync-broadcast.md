<!-- capsule-v2 -->
# Meta-sync socket broadcast — after a schema sync job finishes, how do other instances and the UI learn about it without polling?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the meta-sync processor notify both same-process sockets and cross-instance listeners?

## broadcastEvent with socket-id exclusion
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/meta-sync/meta-sync.processor.ts:MetaSyncProcessor.job/metaDiffJob` (19-100).
**Signature:** `job(job: Job): Promise<void>`; `metaDiffJob(job): Promise<result>` (read-only diff variant returning its result as job result).
**Data Shape:** payload `{context: {base_id, source_id}, action: 'source_meta_sync'}`; `sourceId === 'all'` selects whole-base sync vs single-source.

### Decisive source
```ts
if (info.sourceId === 'all') {
  await this.metaDiffsService.metaDiffSync(context, { baseId, logger: logBasic, req });
} else {
  await this.metaDiffsService.baseMetaDiffSync(context, { baseId, sourceId, logger: logBasic, req });
}
NocoSocket.broadcastEvent(
  context,
  { event: EventType.META_EVENT,
    payload: { action: 'source_meta_sync',
               payload: { base_id: baseId, source_id: info.sourceId } } },
  context.socket_id,          // exclude the requesting client's own socket
);
```

**Flow:** sync runs through MetaDiffsService with a per-line logger that mirrors into job logs (live progress via jobs-log); on completion a single typed event fans out to all connected sockets EXCEPT the originator's. The sibling `metaDiffJob` computes the diff without applying and returns it — the controller uses it for preview.
**Invariant:** the third argument is an exclusion id, not a target id — forgetting it makes the initiating client receive a duplicate refresh. `'all'` vs specific sourceId changes only the service call; the broadcast payload always carries the concrete source_id so clients can scope their refetch.
**Probe:** no unit test upstream. Source-grounded probe: `meta-sync.processor.ts:37-50` — branch pair feeding one shared completion path; `:52-65` — broadcastEvent call signature with socket_id exclusion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "MetaSyncProcessor broadcastEvent metaDiffSync META_EVENT", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt complete-then-broadcast with self-exclusion and the preview/apply split (diff-only variant returning results); adapt event names and socket layer to host; omit the debug-log plumbing shape if you have structured logging. Coverage caveat: no in-repo tests; source-grounded.
