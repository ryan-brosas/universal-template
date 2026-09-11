<!-- capsule-v2 -->
# Post-commit cascade orchestration — how do schema statements, cycle detection, self-backfill, and dependent-field cascades sequence inside one repository update?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** In what order does a table update run DDL → cycle check → backfill → cascade, and why is the DISTINCT filter conditionally skipped?

## PostgresTableSchemaRepository.update + ComputedFieldCascadeAfterSchemaUpdate
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/repositories/PostgresTableSchemaRepository.ts` — update() (:703–846), `ensureDeferredForeignKeys` (:234–301), `scheduleDeferredBackfillAfterUpdate` (:1010–1032); cascade service `src/record/computed/ComputedFieldCascadeAfterSchemaUpdate.ts` whole (251L); cycle gate `schema/helpers/detectCircularDependency.ts`.
**Signature:** `update(context, table, mutateSpec): Promise<Result<Table, DomainError>>`; cascade input `{table, selfBackfillFieldIds, valueChangedFieldIds, deferredBackfillFieldIds?, hasDbStorageTypeChange?}`.
**Data Shape:** three collector visitors feed the pipeline: DependencyChangeDetectorVisitor (needsCheck + changed field ids), FieldValueChangeCollectorVisitor ({selfBackfill, valueChanged, deferredBackfill} sets + dbStorageTypeChanged flag), TableAddFieldCollectorVisitor (added fields for full backfill).

### Decisive source
```ts
// update() ordering:
yield* mutateSpec.accept(visitor);                 // build statements
await executeScopedTableSchemaStatements(...);      // DDL; unique/not-null violations
                                                    // mapped to typed domain errors
if (dependencyDetector.needsCheck()) {              // cycle check AFTER DDL succeeds
  const graph = await fieldDependencyGraph.load(baseId, context,
    { requiredFieldIds: dependencyChangedFieldIds });
  yield* detectCircularDependency(graph.edges);     // Kahn + DFS cycle-path error
}
// added fields: skipDistinctFilter=true (no prior values ⇒ compare nothing)
// cascades:     skipDistinctFilter=hasDbStorageTypeChange (stale column types make
//                IS DISTINCT FROM comparisons UNSAFE ⇒ recompute every row)
```

**Flow:** ensureDbFieldNames → visitor statements → scoped execution w/ violation mapping (`validation.field.unique`, not-null violation enriched with field names) → optional cycle gate → collect value changes → full backfill of newly added fields (with oneMany two-way inclusion when any added field is such a link) → cascade service: self-backfill changed computed fields → plan dependents via ComputedUpdatePlanner (`cyclePolicy:'skip'`) → execute steps level-ascending across tables (lazy-loading foreign tables via dynamic TableByIdSpec import), symmetric-link fields resolved on their FOREIGN table → refresh in-memory select options → emit RecordsBatchUpdated → schedule DEFERRED backfills via `scheduleTableUpdateDeferredTask` (link relationship changes replay post-commit against latest table).
**Invariant:** deferred ids are filtered OUT of immediate passes and replayed exactly once after commit; backfill bookkeeping (`backfilledFieldIdSet`) prevents double-backfilling a field reached by both self and cascade paths.
**Probe:** graph probes: trace_path inbound on `SchemaRuleResolver.resolve` (56 callers incl. planner/repairer/createVisitor); source pins cited inline. No direct unit spec covers update() composition — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ComputedFieldCascadeAfterSchemaUpdate detectCircularDependency scheduleDeferredBackfillAfterUpdate", limit: 10 });
```

## Verdict
Adopt the DDL→cycle-gate→backfill→cascade ordering, conditional DISTINCT skipping on storage-type drift, level-ordered cross-table cascade with symmetric handling, and post-commit deferred replay; adapt the collector-visitor trio shape to host spec system; omit Effect/di token specifics.
