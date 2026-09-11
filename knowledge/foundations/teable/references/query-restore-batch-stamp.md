<!-- capsule-v2 -->
# Provision-state restore — how do soft-deleted tables come back WITH exactly the children deleted alongside them?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does one statement restore a table and only the fields/views sharing its deletion timestamp, while permanent delete handles optional trash tables?

## Shared-timestamp batch restore + to_regclass-guarded permanent purge
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRepository.ts`: `restore` (:1212-1271: MATERIALIZED CTE + three UPDATE…FROM (SELECT deleted_time) branches), `delete` (:1119-1209: permanent mode :1131-1165 with `relationExists` :2338-2346), child-deletion filter `shouldFilterDeletedChildren` (:90-91: active|activeWithPending|activeAnyProvision).
**Signature:** `restore(context, table): Promise<Result<void, DomainError>>` — notFound when zero rows updated.
**Data Shape:** deletion timestamp doubles as BATCH ID; restore also resets `provision_state='ready'`.

### Decisive source
```sql
WITH deleted_table AS MATERIALIZED (
  SELECT "deleted_time" FROM "table_meta"
  WHERE "id" = $1 AND "deleted_time" IS NOT NULL FOR UPDATE
), restored_table AS (
  UPDATE "table_meta" SET "deleted_time"=NULL, …, "provision_state"='ready'
  WHERE "id"=$1 AND "deleted_time"=(SELECT "deleted_time" FROM deleted_table) RETURNING "id"
), restored_fields AS (
  UPDATE "field" SET "deleted_time"=NULL, …
  WHERE "table_id"=$1 AND "deleted_time"=(SELECT "deleted_time" FROM deleted_table) RETURNING "id"
) …
SELECT count(*)::integer AS "updatedRows" FROM restored_table
```
```ts
const relationExists = async (db, name) => (await db.executeQuery(
  sql`SELECT to_regclass(${name}) IS NOT NULL as "exists"`.compile(db))).rows[0]?.exists === true;
```

**Flow:** lock + read the table's deletion stamp → children updated ONLY where their deleted_time EQUALS that stamp (fields/views deleted BEFORE the table keep their own tombstones; ones deleted after an earlier restore are untouched) → count from restored_table decides ok/notFound. Permanent mode purges reference rows by field subselects, skips record_trash/table_trash/trash statements when those tables don't exist (to_regclass probe), then views→fields→table_meta.
**Invariant:** The shared timestamp IS the V1 trash contract (comment at :1222-1223) — restoring must never resurrect independently-deleted children. MATERIALIZED prevents CTE inlining from re-evaluating the locked select. Purge order respects FK direction and tolerates missing trash tables without migrations.
**Probe:** `PostgresTableRepository.spec.ts` covers delete/restore paths; parse_partial flag = line 1224 only.
**Coverage caveat:** restore's cross-timestamp exclusion is pinned via spec fixtures; permanent-mode trash-table probing verified by source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableRepository restore relationExists provision_state", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt timestamp-as-batch-id restore and to_regclass optional-table guards; adapt state enums; never "simplify" to deleting all children's tombstones — that breaks independent deletes.
