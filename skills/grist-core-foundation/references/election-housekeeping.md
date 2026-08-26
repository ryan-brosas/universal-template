<!-- capsule-v2 -->
# Election-Gated Housekeeping — how do N identical servers run a periodic job exactly once without a coordinator?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the pattern for cron-style maintenance (trash collection, metrics, version checks) across replicas that must neither duplicate work nor skip it?

## Named TTL election per task + last-minute soft-delete recheck + permit-scoped self-calls
**Path/Symbol:** `app/gen-server/lib/Housekeeper.ts` — scheduler `start()/stop()` (91–130, one setInterval per task from `Timings` :34–55), exclusive gates `deleteTrashExclusively` (135–144), `logMetricsExclusively` (283–292), `checkVersionUpdatesExclusively` (354–364), `deleteStaleOAuthClientsExclusively` (216–222) — all via `this._electionStore.getElection(name, period/2)`; trash sweep `deleteTrash` (149–211); support endpoints `_withSupport` (532–555); cooperative yielding `forEachWithBreaks` (563–581). Election contract: `app/server/lib/IElectionStore.ts:12`, implementations in `DocWorkerMap.ts:124/:546`; direct test `test/gen-server/lib/Housekeeper.ts:150`.
**Signature:** `getElection(name: string, durationInMs: number): Promise<string | null>` — null means "someone else holds or recently held it"; winners keep the secret key for `removeElection`.
**Data Shape:** deletion candidates come from TypeORM queries keyed on `COALESCE(docs.removed_at, workspaces.removed_at) <= now()-30d` (docs), empty-workspace check via `docs.id IS NULL` anti-join (workspaces), and `trunk_id IS NOT NULL AND updated_at <= threshold` (forks); thresholds are built IN SQL (`fromNow(dbType, "-30 days")`) because TypeORM date handling differs per dialect.

### Decisive source
```ts
public async deleteTrashExclusively(): Promise<boolean> {
  const electionKey = await this._electionStore.getElection("housekeeping", Timings.DELETE_TRASH_PERIOD_MS / 2.0);
  if (!electionKey) {
    log.info("Skipping deleteTrash since another server is working on it or worked on it recently");
    return false;
  }
  this._electionKey = electionKey;
  await this.deleteTrash();
  return true;
}
...
// inside deleteTrash — the last-minute recheck:
if (doc.removedAt === null && doc.workspace.removedAt === null) {
  throw new Error(`attempted to hard-delete a document that was not soft-deleted: ${doc.id}`);
}
```
Fork deletion shows the permit discipline: `setPermit({docId})` → authenticated DELETE through the public API with the `Permit` header → `finally { removePermit(permitKey) }`.

**Flow:** each interval fires on every replica ⇒ every replica asks the shared store for the named election with TTL = HALF the task period (so at most one winner per window, and a crashed winner's TTL expires before the next tick) ⇒ losers log-and-return ⇒ winner sweeps docs (routing each hard-delete through its assigned doc worker via `server.hardDeleteDoc`), then workspaces (only after they're empty), then forks (via permit-scoped API DELETEs), swallowing per-doc ApiErrors so one bad doc can't block the queue. The same election wrapper is reused verbatim for four different tasks; metrics loops additionally yield every ~50ms of synchronous work (`forEachWithBreaks`) so logging thousands of rows can't starve the event loop.
**Invariant:** exclusivity is TIME-based, not lock-based: no mutex is held during the sweep — correctness rests on TTL > half-period overlap math and idempotent sweeps. Soft-delete state is RE-VERIFIED immediately before every hard delete because minutes may have passed since the query ran (undeletes race). Hard deletes always go through the document's own worker/API rather than raw DB/file access, keeping storage ownership rules intact. Election secrets enable explicit early release (`testClearExclusivity`). A porter who uses TTL = full period will get skipped ticks when runs are slow; who skips the recheck will hard-delete resurrected documents.
**Probe:** direct test `test/gen-server/lib/Housekeeper.ts:150` "enforces exclusivity of housekeeping" asserts first call wins (`true`), immediate second and third calls lose (`false`), and post-`testClearExclusivity` a new election succeeds; :82 "can delete old soft-deleted docs and workspaces" and :160 "can delete old forks" pin sweep behavior end-to-end.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "Housekeeper getElection deleteTrashExclusively IElectionStore", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any multi-replica maintenance job: named TTL elections + half-period TTL + last-minute precondition recheck is the whole pattern, reusable for cache pruning, billing sync, or cleanup of any kind. Adapt the election store to your infra (redis SET NX EX maps 1:1). Omit the permit-scoped HTTP self-calls if your workers share a process space — but keep them whenever deletion must respect per-resource service boundaries.
