<!-- capsule-v2 -->
# pg-meta mutation builder plane — how do you compose multi-statement DDL mutations where some statements depend on state only discoverable at runtime?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A dashboard "save table" sends one PATCH with name/schema/RLS/replica-identity/PK/comment changes; a column update may rename, retype, change default/identity/nullability/uniqueness/check. How do these become safe ordered SQL when constraint NAMES (needed to drop constraints) are unknown until execution time?

## Transactional statement ladders with pinned ordering (`pg-meta-tables.ts`, `pg-meta-columns.ts`)
**Path/Symbol:** `packages/pg-meta/src/pg-meta-tables.ts` : `create` (:192-207), `update` (:220-311), `remove` (:167-175); `packages/pg-meta/src/pg-meta-columns.ts` : `create` (:146-208), `update` (:218-379), `remove` (:381-387).
**Signature:** `update(old: Pick<PGTable,'id'|'name'|'schema'>, params): { sql: SafeSqlFragment }` — each builder returns ONE SafeSqlFragment containing a full BEGIN…COMMIT transaction.
**Data Shape:** every multi-statement mutation wraps its statements in `BEGIN; … COMMIT;` unless the caller passes `no_transaction` (create path). Undefined params emit NOTHING (skip), so a partial PATCH renders only the statements it needs. Ordering is pinned by in-source comments because Postgres makes some orderings illegal: tables — "nameSql must be last, right below schemaSql" (RENAME runs after SET SCHEMA and uses the NEW schema); columns — "nameSql must be last. defaultValueSql must be after typeSql. identitySql must be after isNullableSql." Destructive defaults are RESTRICT: `remove` emits `DROP TABLE … CASCADE|RESTRICT` and `DROP COLUMN … CASCADE|RESTRICT` with cascade OPT-IN.

### Decisive source
```ts
// nameSql must be last, right below schemaSql
const sql = safeSql`
BEGIN;
  ${enableRls}
  ${forceRls}
  ${replicaSql}
  ${primaryKeysSql}
  ${commentSql}
  ${schemaSql}
  ${nameSql}
COMMIT;`
```

**Flow:** param → per-param fragment builder (undefined ⇒ empty fragment) → fixed-order concatenation inside one transaction → single SafeSqlFragment to executeSql (pass-1 guard ladder). Fail-loud guards at build time: `replica_identity === 'INDEX'` without `replica_identity_index` throws; column create with both identity and default_value throws ("Columns cannot both be identity and have a default value").
**Invariant:** statement ORDER is part of the contract, not an implementation detail — rename-after-reschema, default-after-type, identity-after-nullability are legal/illegal in Postgres for specific reasons; pin the order in a comment at the concatenation site or a future reorder silently breaks.
**Probe:** DB-backed suites under standing runner block (never claimed passing): `test/tables.test.ts` "create, retrieve, update, and delete table" (:436), "primary keys" (:630), "remove table by id/name" + "remove throws error for non-existent table" (:1111-1156); `test/columns.test.ts` "retrieve, create, update, delete column" (:182), "drop with cascade" (:705), "column with multiple checks" (:745), "dropping column checks" (:819).

## DO $$ blocks for runtime-discovered constraint names (`pg-meta-columns.ts`, `pg-meta-tables.ts`)
**Path/Symbol:** `pg-meta-columns.ts` : unique-drop loop (:302-317), check-constraint replace (:328-356); `pg-meta-tables.ts` : PK drop block (:269-281).
**Signature:** n/a — embedded plpgsql DO blocks inside the transaction.
**Data Shape:** dropping a UNIQUE/PK/CHECK constraint requires its NAME, which is only discoverable at execution time (Postgres auto-names constraints). The builders embed a `DO $$` block that queries pg_constraint by (conrelid, conkey[1] = ordinal_position, contype) and drops via dynamic SQL with `quote_ident(r.conname)` / `format('… DROP CONSTRAINT %I', v_conname)`. The check-constraint ADD additionally ASSERTs the new constraint's conkey refers to EXACTLY this column (`cardinality(v_conkey) = 1 AND v_conkey[1] = ordinal_position`) "so a crafted check can't constrain other columns". The column type change uses `USING col::type` to allow implicit conversion of incompatible types (int4→text).

### Decisive source
```ts
checkSql = safeSql`
DO $$
DECLARE
  v_conname name;
  v_conkey int2[];
BEGIN
  SELECT conname into v_conname FROM pg_constraint WHERE
    contype = 'c'
    AND cardinality(conkey) = 1
    AND conrelid = ${literal(old.table_id)}
    AND conkey[1] = ${literal(old.ordinal_position)}
  ORDER BY oid asc
  LIMIT 1;

  IF v_conname IS NOT NULL THEN
    EXECUTE format('ALTER TABLE ${ident(old.schema)}.${ident(old.table)} DROP CONSTRAINT %I', v_conname);
  END IF;
  ${addCheckSql}
END
$$;`
```

**Flow:** identify the constraint by CATALOG POSITION (table oid + ordinal position + constraint type), not by name → drop-if-exists dynamically → add the new one → assert the new one's key shape. The identity transition uses the same pattern as a decision TABLE (in-source old×new matrix): false⇒DROP IDENTITY IF EXISTS; old-true+new-gen⇒SET GENERATED; new-true⇒ADD GENERATED.
**Invariant:** never hard-code auto-generated constraint names — resolve them from pg_constraint by position at execution time inside a DO block, and validate the RESULTING constraint's shape (conkey) when adding, so a caller-supplied check expression cannot constrain columns it shouldn't.
**Probe:** `test/columns.test.ts` "column with multiple checks" / "column with multiple unique constraints" / "dropping column checks" (:745/:782/:819) and `test/tables.test.ts` "primary keys" (:630) — DB-backed, standing runner block.

## Drop/recreate ladder when ALTER cannot express the transition (`pg-meta-publications.ts`)
**Path/Symbol:** `packages/pg-meta/src/pg-meta-publications.ts` : `create` (:82-120), `update` (:132-238), `remove` (:240-243).
**Signature:** `update(id: number, params): { sql: SafeSqlFragment }` — a single DO $$ block.
**Data Shape:** ALTER PUBLICATION cannot move between a table LIST and ALL TABLES, so the update DO block drops and recreates the publication ONLY on that transition (`execute(format('drop publication %1$I; create publication %1$I [for all tables];', old.pubname))`); otherwise it alters in place (drop-all-tables then add-new-list, set publish flags via `coalesce(new_x, old.pubx)`, owner, rename-skipped-when-unchanged — "Using the same name in the rename clause gives an error"). Two post-recreate hazards are handled explicitly: the oid CHANGES on recreate, so the block records the surviving NAME in `create temp table pg_meta_publication_tmp (name) on commit drop as values (...)` because "DO blocks can't return a value"; and create's table list splits each entry on the FIRST dot only (`const [schema, ...rest] = t.split('.')`) so quoted table names containing dots survive.

### Decisive source
```sql
elsif new_tables = 'all tables' then
  if old.puballtables then
    null;
  else
    -- Need to recreate because going from list of tables <-> all tables with alter is not possible.
    execute(format('drop publication %1$I; create publication %1$I for all tables;', old.pubname));
  end if;
```

**Flow:** read current state from catalog (`select * into old from pg_publication where oid = id`, raise if missing) → classify the transition → minimal alter OR targeted recreate → publish/owner/rename alters → record identity for the caller's follow-up retrieve.
**Invariant:** when the platform DDL lacks an in-place transition, recreate is acceptable ONLY if (a) it fires on that transition alone, (b) identity for follow-up reads survives the recreate (name, not oid), and (c) the whole ladder runs in one atomic unit.
**Probe:** `test/publications.test.ts` "retrieve, create, update, delete" (:33) exercises create→update→retrieve→remove round-trips — DB-backed, standing runner block.

## Studio consumer bridge
**Path/Symbol:** `apps/studio/data/tables/table-{create,delete,update}-mutation.ts` (whole-file reads of create/delete).
**Signature:** `deleteTable({ projectRef, connectionString, id, name, schema, cascade = false })` → `pgMeta.tables.remove({name, schema}, {cascade})` → `executeSql({ projectRef, connectionString, sql, queryKey })`.
**Data Shape:** each studio mutation is builder → pass-1 executeSql guard ladder → hand-listed cache invalidation in onSuccess. Delete invalidates CROSS-ENTITY keys (tableEditor, table list, infiniteListPrefix, entityTypeKeys.list, viewKeys.listBySchema — dropping a table breaks views); create invalidates both includeColumns variants plus privileges. onError defaults to `toast.error('Failed to delete database table: ' + data.message)`.

### Decisive source
```ts
await Promise.all([
  queryClient.invalidateQueries({ queryKey: tableEditorKeys.tableEditor(projectRef, id) }),
  queryClient.invalidateQueries({ queryKey: tableKeys.list(projectRef, schema) }),
  queryClient.invalidateQueries({ queryKey: tableKeys.infiniteListPrefix(projectRef, schema) }),
  queryClient.invalidateQueries({ queryKey: entityTypeKeys.list(projectRef) }),
  // invalidate all views from this schema
  queryClient.invalidateQueries({ queryKey: viewKeys.listBySchema(projectRef, [schema]) }),
])
```

**Flow:** UI action → typed variables → builder renders SafeSqlFragment → executeSql (size cap, EXPLAIN preflight option, impersonation rewind) → onSuccess invalidates the hand-listed key set → onError toast fallback.
**Invariant:** destructive mutations must invalidate the keys of entities that DEPEND on the target (views on a dropped table), not just the target's own keys — the dependency list is hand-maintained per mutation and is the porting checklist.
**Probe:** direct read at the pin; no dedicated test for the studio mutation wrappers (they compose already-tested pieces — recorded as consumer-only).

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads plus the direct tests at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "pgMeta tables remove create update publications update DO block quote_ident conrelid", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: one-transaction-per-mutation fragments with undefined-param-skip semantics; pinned statement ordering documented at the concatenation site; RESTRICT-default destructive ops with opt-in cascade; build-time fail-loud guards for mutually exclusive params; DO $$ blocks that resolve auto-named constraints from pg_constraint by position and validate resulting conkey shape; recreate-only-on-impossible-transition ladders with name-based post-recreate identity; cross-entity invalidation lists on destructive consumers. Adapt the constraint-position predicates to your catalog layout. Omit Supabase-product specifics: the exact key factories and toast copy. Direct-test caveat: four DB-backed suites read at the pin under the standing runner block — never claimed passing.
