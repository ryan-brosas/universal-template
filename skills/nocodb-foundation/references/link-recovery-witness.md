<!-- capsule-v2 -->
# Link recovery migration — how do you reconstruct a lost LTAR colOptions row from the surrounding meta graph, or delete the column when it's unrecoverable?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** Given a LinkToAnotherRecord column with no COL_RELATIONS row, what evidence pins its related table and inverse type?

## Witness-driven inversion ladder inside one transaction
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_003_recover_links.ts:job` (:22-323).
**Signature:** broken set = `COLUMNS ⋈ LEFT JOIN COL_RELATIONS WHERE uidt='LinkToAnotherRecord' AND COL_RELATIONS.id IS NULL`; per column, candidate witnesses probed in order: lookups → rollups → all links pointing AT this table; insert via `ncMeta.startTransaction()` with commit/rollback at the ends.
**Data Shape:** recovered COL_RELATIONS row = `{id (fresh nanoid), fk_column_id, fk_related_model_id, created_at/updated_at/virtual/base_id COPIED FROM THE WITNESS LINK, fk_workspace_id only when isEE}`.

### Decisive source
```ts
} else if (link.type === RelationTypes.BELONGS_TO) {
  // a broken bt column is proven by an hm twin on the same FK pair:
  columnInCurrTable = await ncMeta.knex(COL_RELATIONS).join(COLUMNS, …)
    .where(REL.fk_related_model_id, relatedTableId)
    .where(REL.type, RelationTypes.HAS_MANY)              // INVERSE type
    .where(REL.fk_child_column_id,  link.fk_child_column_id)   // same FK pair
    .where(REL.fk_parent_column_id, link.fk_parent_column_id)
    .first();
}
// …and for the mm case BOTH mm columns are swapped:
case RelationTypes.MANY_TO_MANY:
  await ncMeta.knex(COL_RELATIONS).insert({ ...commonProps,
    type: RelationTypes.MANY_TO_MANY,
    fk_child_column_id: link.fk_parent_column_id,          // swapped
    fk_parent_column_id: link.fk_child_column_id,          // swapped
    fk_mm_model_id: link.fk_mm_model_id,
    fk_mm_child_column_id: link.fk_mm_parent_column_id,    // swapped
    fk_mm_parent_column_id: link.fk_mm_child_column_id }); // swapped
```

**Flow:** find orphaned relation columns → for each, try to identify the related table from dependents (any lookup on this relation names its model; then any rollup; fall back to scanning every link whose `fk_related_model_id` = this table) → for each candidate witness of type X probe the opposite table for the INVERSE-type twin on identical FK columns (hm↔bt; oo↔oo; mm with child/parent AND mm_child/mm_parent swapped) → if found, INSERT the colOptions row copying timestamps/virtual/base from the witness (never invent them); if NO witness maps, `Column.delete` the broken column — unrecoverable links are removed, not guessed.
**Invariant:** the inverse-mapping matrix (hm↔bt swap-free, oo identity, mm double-swap) is the porting payload — getting one arm wrong silently creates wrong-direction relations. Evidence order matters: lookups/rollups are cheap and precise; the scan fallback can mis-pick between multiple candidate tables, so it runs LAST. The first matching witness wins (`break` after insert), keeping recovery deterministic under duplicates. Whole run is ONE transaction: partial recovery would leave meta worse than before.
**Probe:** no unit test upstream. Source-grounded probe: LEFT JOIN … IS NULL selector :28-37; mm swap :279-288 vs probe-time mirror swap :210-221; delete-fallback :297-310; single commit :316.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "RecoverLinksMigration columnInCurrTable RelationTypes BELONGS_TO MANY_TO_MANY fk_mm", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the witness-inversion ladder + delete-when-unrecoverable rule for any referential-meta repair; adapt the witness kinds to your dependency columns; omit the EE workspace-id branch if you have no workspace scoping.
