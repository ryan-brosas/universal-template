<!-- capsule-v2 -->
# Computed event fan-out — how do inline recomputation results become realtime events, and why is newVersion derived as oldVersion+1 instead of read?

## group changesByStep by table → one RecordsBatchUpdated per table → publish afterCommit; version arithmetic is contractual
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `buildComputedUpdateEvents(changesByStep, baseId, orchestration)` (:4072–4122, version derivation :4099–4108), `publishComputedUpdateEvents` (:3858–3891, afterCommit registration :3886), `resolveComputedRealtimeOrchestration` (:4124–4129, `orchestration ?? core.buildOperationBatchMutation(context.requestId, recordCount)`), extractors `extractChangesForRecord` (:4131–4148) / `extractChangesForAllRecords` (:4156–4175).
**Signature:** input `ComputedUpdateResult['changesByStep']: Array<{tableId, recordChanges: Array<{recordId, oldValue, changes: [{fieldId, oldValue, newValue}]}>}>`; output `RecordsBatchUpdated[]`.

### Decisive source
```ts
const updates = recordChanges.map((change) => ({
  recordId: change.recordId,
  oldVersion: change.oldVersion,
  newVersion: change.oldVersion + 1,          // NOT read from the row
  changes: change.changes.map(fc => ({fieldId: fc.fieldId, oldValue: fc.oldValue, newValue: fc.newValue})),
}));
events.push(core.RecordsBatchUpdated.create({tableId, baseId, updates, source: 'computed', orchestration}));
...
const publish = async () => { const r = await this.eventBus.publishMany(core.withoutTransaction(context), events);
  if (r.isErr()) this.logger.warn('computed:events_publish_failed', {...}); };
if (core.registerAfterCommit(context, publish)) return;
await publish();
```

**Flow:** fold per-step changes into per-table buckets (invalid TableIds silently skipped) → mint one batch event per table with source='computed' → register the bus publish on afterCommit (or fire immediately when no tx is active); publish failures log-warn only.
**Invariant:** THREE traps: (1) `newVersion = oldVersion + 1` is DERIVED because computed steps execute via UPDATE…FROM-SELECT that does not RETURN versions per record — clients reconcile by expecting exactly one bump per event, so reading a real (possibly multi-bumped) version would break optimistic-concurrency on the client. (2) Events carry field-level old+new values, not whole rows — consumers patch cells incrementally. (3) Publishing must happen AFTER commit (`registerAfterCommit`) or realtime subscribers would read stale committed state and self-heal-loop; failure to publish degrades to a missed push (clients refetch), never an error surfaced to the writer.
**Probe:** deterministic grep: version math :4102, afterCommit gate :3886.
**Coverage caveat:** no dedicated spec isolates buildComputedUpdateEvents; exercised through hybrid/async suites (update.spec.ts :2002ff) — noted.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildComputedUpdateEvents RecordsBatchUpdated publishComputedUpdateEvents", limit: 5 });
```
## Verdict
Adopt for derived-write notifications: per-table batch events with derived version bumps, post-commit publication, warn-don't-fail delivery.
