<!-- capsule-v2 -->
# Orphan view-column cleanup — how do you garbage-collect dangling per-view rows left by non-cascading meta deletes, and which jobs deliberately stay empty?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What does the pure-knex anti-join delete look like on all meta DBs, and why do some versioned jobs ship as deliberate no-ops?

## Per-table NOT EXISTS delete + the no-op census
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_014_cleanup_orphan_view_columns.ts:job` (:44-81) over VIEW_COLUMN_TABLES (:36-43); no-op twins `nc_job_004_cleanup_duplicate_column.ts` ("cloud only migration so keep as empty", 20L) and `nc_job_no_op.ts` (8L); CE-stub twin `migration-ce-stub-parity.md`.
**Signature:** `knex(table).whereNotNull('fk_column_id').whereNotExists(select 1 from COLUMNS whereRaw('COLUMNS.id = table.fk_column_id')).delete()` per view-column table; best-effort try/catch per table.
**Data Shape:** six target tables (GRID/FORM/KANBAN/GALLERY/CALENDAR/MAP `_VIEW_COLUMNS`), each carrying `fk_column_id`.

### Decisive source
```ts
// Pure-knex anti-join delete per table so it runs on any meta DB. Table
// names come from the MetaTable enum (constants), not user input.
for (const table of VIEW_COLUMN_TABLES) {
  try {
    const deleted = await knex(table)
      .whereNotNull('fk_column_id')
      .whereNotExists(function () {
        this.select(knex.raw('1')).from(MetaTable.COLUMNS)
          .whereRaw(`${MetaTable.COLUMNS}.id = ${table}.fk_column_id`);
      })
      .delete();
  } catch (e) { this.logger.warn(`Orphan view-column cleanup skipped ${table}: …`); }
}
```

**Flow:** for each of the six view-column tables run a correlated NOT EXISTS anti-join against `nc_columns_v2` and delete dangling rows → log per-table counts → never abort: one failing table is a warning, the rest still clean. The header documents WHY the orphans exist (raw `metaDelete` callers like the Links V1→V2 FK removal bypass `Column.delete`'s cascade) and why it's a background JOB not a boot knex migration (the anti-join can be slow; startup must not wait).
**Invariant:** column ids are globally unique nanoids, so "no nc_columns row anywhere" genuinely means orphaned — cross-base links always reference an EXISTING local column and are safe from the sweep. Idempotent by construction (re-run finds zero). The deliberate no-op jobs are part of the contract too: `_004` keeps its version slot occupied for cloud-only behavior and `no_op` exists for slot alignment — deleting them would desync version numbering (see migration-ce-stub-parity).
**Probe:** no unit test upstream. Source-grounded probe: header rationale :19-34; function-style whereNotExists (needed for `this` binding) :52-57; `_004` body is a comment plus `return true`.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "CleanupOrphanViewColumnsMigration VIEW_COLUMN_TABLES whereNotExists NoOpMigration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the constant-table anti-join sweep + warn-and-continue loop for referential garbage collection; adapt target tables; keep your own no-op slot fillers — never renumber.
