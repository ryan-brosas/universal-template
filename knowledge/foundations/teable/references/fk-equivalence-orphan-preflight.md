<!-- capsule-v2 -->
# FK equivalence + orphan preflight — why is "constraint exists by name" the wrong validity check, and what must be verified before adding a foreign key?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do rules treat an equivalently-shaped FK with a different name as valid, and how do they avoid failed ALTERs on orphaned data?

## ForeignKeyDiagnostics + DO-block conditional FK
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/helpers/ForeignKeyDiagnostics.ts` whole (127L); DO-block builder `rules/helpers/StatementBuilders.ts` `createForeignKeyConstraintStatement` (:113–190); consumer JunctionTableForeignKeyRule.isValid (:858–1010).
**Signature:** `countOrphanForeignKeyRows(db, source{schema,table}, column, target, '__id'): Result<number>`; `foreignKeyExistsForColumnTarget(...): Result<boolean>`; statement factory `(source, constraintName, column, target, '__id', onDelete='CASCADE', targetTableMetaId?)`.
**Data Shape:** equivalence check matches single-column FKs by (source schema.table.column) → (target schema.table.column) via pg_constraint conkey/confkey WITH ORDINALITY position joins — NAME-INSENSITIVE.

### Decisive source
```sql
-- equivalent-FK probe: shape-based, not name-based
SELECT EXISTS (SELECT 1 FROM pg_constraint con ...
  WHERE con.contype='f' AND array_length(con.conkey,1)=1 AND array_length(con.confkey,1)=1
    AND source_schema.nspname=$1 AND source_table.relname=$2 AND source_attr.attname=$3
    AND target_schema.nspname=$4 AND target_table.relname=$5 AND target_attr.attname=$6)

-- creation: resolve target THROUGH meta at execute time, skip if missing,
-- swallow duplicate_object so replays stay idempotent
IF EXISTS (SELECT 1 FROM information_schema.tables
           WHERE table_schema=resolved_target_schema AND table_name=resolved_target_table) THEN
  BEGIN EXECUTE format('ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ... ON DELETE CASCADE');
  EXCEPTION WHEN duplicate_object THEN NULL; END;
END IF;
```

**Flow:** isValid ladder: named constraint exists⇒valid → else resolve physical target (metaId→db_table_name, honoring deleted_time IS NULL) → equivalent-shape FK exists⇒VALID (never recreate) → count orphans: >0 ⇒ coded manual-repair failure; =0 ⇒ plain auto up(). Repair deletes orphans via NOT EXISTS anti-join then re-adds with CASCADE.
**Invariant:** a differently-named FK with identical columns satisfies the rule — porters who key validity on constraint NAME create perpetual repair loops after restores/renames; orphan counting happens BEFORE any ALTER attempt because a failed ADD CONSTRAINT inside a big transaction is expensive to unwind.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/SchemaRules.pglite.spec.ts:1601 'should create FK constraint against resolved physical table name'`, :1638 'repair FK when logical target resolves to a physical table', :1704 'repair unavailable when the target table is missing', :2553 junction variant.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "foreignKeyExistsForColumnTarget countOrphanForeignKeyRows createForeignKeyConstraintStatement", limit: 10 });
```

## Verdict
Adopt shape-based FK equivalence, orphan-count preflight gating auto vs manual repair, meta-mediated target resolution, and duplicate_object-swallowing idempotent creation; adapt catalog queries to host PG version assumptions; omit CASCADE default if host semantics differ.
