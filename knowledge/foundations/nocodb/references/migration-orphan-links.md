<!-- capsule-v2 -->
# Orphan cross-base link reaper — JOIN-based orphan detection gated on the OWNING column's soft-delete state

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** When a cross-base link's target table is purged, how does cleanup find and delete the dangling link (plus its lookups/rollups) without breaking trash/restore?

## Path/Symbol
`packages/nocodb/src/modules/jobs/migration-jobs/nc_job_013_cleanup_orphan_cross_base_links.ts:CleanupOrphanCrossBaseLinksMigration.job` (44–159).

**Signature:** `job(): Promise<boolean>` — single meta-DB pass, idempotent, returns true always.

**Data Shape:** one pure-knex query over `nc_col_relations cr` LEFT JOIN `nc_models m` ON (`m.id = cr.fk_related_model_id` AND `m.base_id = cr.fk_related_base_id`) LEFT JOIN `nc_columns oc` ON (`oc.id = cr.fk_column_id` AND `oc.base_id = cr.base_id`); orphan predicate in JS: `fk_related_base_id !== base_id && !own_col_deleted && (related_model_id == null || related_model_deleted)`.

### Decisive source
```ts
// The owning-column check is critical (#9392): trash/restore SOFT-deletes the owning
// link column when its related table is trashed — that link is restore-PENDING. The
// relation row is NOT soft-deleted by teardown, so gating on cr.deleted would never
// exclude it; we must gate on the OWNING COLUMN's deleted state. Reaping a
// soft-deleted link would hard-delete it and break restore.
const orphans = rows.filter(r =>
  r.fk_related_base_id !== r.base_id &&      // genuinely cross-base
  !r.own_col_deleted &&                      // owning column LIVE — leave restore-pending alone
  (r.related_model_id == null || r.related_model_deleted));
// dependents BEFORE the link: rollups/lookups reference it via fk_relation_column_id
for (const depTable of [MetaTable.COL_ROLLUP, MetaTable.COL_LOOKUP]) {
  for (const dep of await ncMeta.metaList2(ws, base, depTable, { condition: { fk_relation_column_id: rel.fk_column_id } })) {
    if (!dep.fk_column_id) continue;
    await Column.delete2(ctx, { id: dep.fk_column_id, includeDeleted: true }, ncMeta);
  }
}
await Column.delete2(ctx, { id: rel.fk_column_id, includeDeleted: true }, ncMeta);
```

**Flow:** dialect gate first — non-PG meta DBs can't hold cross-base rows, skip the scan entirely and return true. Then one seq-scan query (cross-base links are rare), JS-side orphan filter, per-orphan best-effort reap in the LINK's own base context: dependent Rollup/Lookup columns deleted before the link column itself via `Column.delete2` (removes column + colOptions + busts cache). Failures are logged-and-skipped, never aborting the job.

**Invariant:** the soft-delete state machine has TWO layers and only one is authoritative here — a relation row whose owning column is soft-deleted is RESTORE-PENDING, not garbage; hard-deleting it destroys restore. Dependents must be reaped before their link or `delete2` leaves dangling rollup/lookup option rows. Boolean/cross-base checks run in JS (not SQL) to stay dialect-agnostic across meta stores.

**Probe:** no unit test upstream. Source-grounded probe: doc comment lines 8–34 (strategy + EE/pg-only note), `:47-54` (clientType gate), `:62-69` (the #9392 owning-column rationale verbatim), `:101-106` (three-clause orphan predicate), `:120-135` (dependents-first order), `:147-152` (skip-don't-abort).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "CleanupOrphanCrossBaseLinksMigration Column.delete2 fk_related_base_id COL_RELATIONS", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the owning-column-gated orphan predicate, dependents-before-link deletion, and dialect early-exit; adapt table names to host; omit cross-base contexts unless porting multi-base links. Coverage caveat: no in-repo unit tests; source-grounded.
