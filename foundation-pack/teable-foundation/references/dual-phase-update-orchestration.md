<!-- capsule-v2 -->
# Dual-phase update orchestration — where do locks, the base write, and computed publishing go inside one transaction?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** In what ORDER must impact collection, record locking, the caller's update callback, and op publication execute?

## computeCellChangesForRecordsMulti
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-orchestrator.service.ts:ComputedOrchestratorService.computeCellChangesForRecordsMulti` (:59–177; entry wrapper :42–52; lock helper :360–447; domain resolution :449–528).
**Signature:** `computeCellChangesForRecordsMulti(sources: Array<{tableId, cellContexts}>, update: (tableDomains?) => Promise<void>): Promise<{ publishedOps, impact }>`.

### Decisive source
```ts
// class docstring :32–38
// - Builds setRecord ops and saves them as raw ops; no DB writes, no __version bump here.
// - Raw ops are picked up by ShareDB publisher after the outer tx commits.
await this.lockImpactedRecords(filtered, impactMerged, tableDomains);   // :140 BEFORE update()
...
// 2) Perform the actual base update(s) if provided                     // :167
await update(tableDomains);
// 3) Evaluate and publish computed values                              // :170
const total = await this.evaluator.evaluate(impactMerged, { excludeFieldIds, tableDomains });
```

**Flow:** merge per-source impacts once (Promise.all over collectors, :89–93); drop empty groups (:123–128); resolve domains one-hop (`getAllForeignTableIds`, deeper deps resolved via persisted physical columns — comment :492–493); lock impacted records SORTED BY dbTableName (:433 — deterministic ordering deadlock-avoidance), gated on `typeof dbProvider.lockRecordsSql === 'function'` (:365 capability probe); THEN run the caller's update; THEN evaluate+publish. Publishing EXCLUDES base-changed fields (`excludeFieldIds`) EXCEPT track-all LastModified* audit fields which are re-admitted so their externally-computed values get published (:142–165).
**Invariant:** The orchestrator never writes computed values to the DB — persistence belongs to the evaluator's UPDATE...FROM SELECT; ops saved here are RAW and versionless, flushed post-commit by ShareDB. Locks before update() prevent concurrent computed writers interleaving between read and write. Track-all audit re-admission must delete from the exclusion set AFTER domains resolve (order at :144 vs :160–163).
**Probe:** needles verified at this pin (:36 docstring publish-only, :140 lock-before-update, :168 update call); graph retrieval `lockImpactedRecords` resolves :360–447.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "lockImpactedRecords", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt collect→lock(sorted)→update→evaluate ordering and the publish-only doctrine; adapt the lock-SQL capability probe to your dialect surface; omit NestJS decorators. Field create/update/delete variants live in the same file (:185–357): pre-delete filters post-update existence (:236–278) — port that too if you support destructive schema ops.
