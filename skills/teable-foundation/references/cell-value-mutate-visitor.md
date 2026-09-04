<!-- capsule-v2 -->
# CellValueMutateVisitor — how one record UPDATE compiles from a typed spec

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a porter applies a set of typed cell-value specs to one record, what SQL does the visitor emit and what invariants (system columns, computed skip, link junction/FK routing) must not be broken?

## Cell-mutation visitor
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/visitors/CellValueMutateVisitor.ts` (`CellValueMutateVisitor`, 101-926).
**Signature:** `CellValueMutateVisitor.create(db, table, tableName, ctx).accept(spec) → then .build() → Result<MutationStatements, DomainError>`; `MutationStatements = { mainUpdate, setClauses, additionalStatements, changedFieldIds }`.
**Data Shape:** `ctx = { recordId, actorId, now, actorName?, actorEmail?, fillLinkTitles?, fillLinkTitleForeignTables?, deferAttachmentTableReplace? }`. Constructor pre-seeds `setClauses` with `__last_modified_time=now`, `__last_modified_by=actorId`, `__version=__version+1` (SQL ref increment). `build()` returns a shallow copy of setClauses.

### Decisive source
```ts
// constructor
this.setClauses[LAST_MODIFIED_TIME_COLUMN] = this.ctx.now;
this.setClauses[LAST_MODIFIED_BY_COLUMN] = this.ctx.actorId;
this.setClauses[VERSION_COLUMN] = sql`${sql.ref(VERSION_COLUMN)} + 1`;
// build(): applies tracked last-modified fields, then compiles main UPDATE
const mainUpdate = this.db.updateTable(this.tableName)
  .set(this.setClauses).where(RECORD_ID_COLUMN, '=', this.ctx.recordId).compile();
```

**Flow:** constructor seeds system columns → each `visitSet*Value(spec)` pushes a SET clause (+ changedFieldIds) and may push `additionalStatements` (junction/FK ops) → `build()` first runs `applyTrackedLastModifiedTime/ByUpdates` (re-reads lastModified fields, only updates if the field's trackedFieldIds intersect changedFieldIds OR tracked list empty; skips persisted-generated columns; pushes the field id into changedFieldIds so the tracked update itself is a change) → compiles the single main UPDATE.

**Invariant:** `changedFieldIds` is the single source of truth for computed propagation AND for last-modified tracking; a non-system computed field is skipped (not written) unless it is a system computed (createdTime/lastModifiedTime/createdBy/lastModifiedBy/autoNumber) persisted as a generated column — `shouldSkipComputed` returns `true` for non-system computed, else `isPersistedAsGeneratedColumn(field)`.

**Probe:** `record/visitors/CellValueMutateVisitor.spec.ts` — `'applies tracked last-modified fields during build'` (:576), `'uses actor identity context for tracked last-modified-by snapshots'` (:625), `'skips non-system computed fields when setting scalar values'` (:211), `'clears non-link fields directly and records changed ids'` (:230).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "CellValueMutateVisitor build setClauses additionalStatements", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the visitor-as-compiler shape (typed specs → SET clauses + additional statements + changed-field ledger), the system-column seeding, and the computed-skip rule. Adapt the exact SQL-ref version increment (`__version + 1` is teable's optimistic-lock column). Omit the link-junction/FK routing (covered by the dedicated link-mutation capsule). Coverage caveat: 2 parse_partial single-line flags in the file — read source for those lines; probes pinned to the real spec suite.
