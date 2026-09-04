<!-- capsule-v2 -->
# Link-JSON backfill rebuilder — how do you rebuild junction/FK storage FROM the denormalized link cell column?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What SQL restores FK columns or junction rows when the normalized side was lost but the JSON link cell survived?

## backfillForeignKeysFromLinkColumn
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:backfillForeignKeysFromLinkColumn` (:686–924), called from `fixMissingForeignKeyColumns` :668–681.
**Signature:** `backfillForeignKeysFromLinkColumn(params: {dbTableName, linkDbFieldName, fkHostTableName, selfKeyName, foreignKeyName, relationship, isOneWay?, routingTableId})`.
**Data Shape:** Link cells are JSON: scalar `{id}` for ManyOne/OneOne, arrays of `{id}` for array relationships; PG stores jsonb, SQLite stores text JSON.

### Decisive source
```ts
const query =
  this.dbProvider.driver === DriverClient.Pg
    ? this.knex(fkHostTableName)
        .update({
          [foreignKeyName]: this.knex.raw(`NULLIF(??->>'id','')`, [linkDbFieldName]),
        })
        .whereNotNull(linkDbFieldName)
        .whereNull(foreignKeyName)
        .toQuery()
```
(OneMany non-junction dedup — first writer wins:)
```sql
WITH pairs AS (
  SELECT s.__id AS self_id, (elem->>'id') AS foreign_id
  FROM ?? AS s
  JOIN LATERAL jsonb_array_elements(??.??) elem ON true
  WHERE ??.?? IS NOT NULL
), dedup AS (
  SELECT foreign_id, MIN(self_id) AS self_id
  FROM pairs WHERE foreign_id IS NOT NULL
  GROUP BY foreign_id
)
UPDATE ?? AS f SET ?? = d.self_id FROM dedup d
WHERE f.__id = d.foreign_id AND f.?? IS NULL
```
(Junction variant inserts `SELECT DISTINCT … WHERE NOT EXISTS` pairs.)

**Flow:** Column-existence preflight per driver (jsonb_array_elements vs json_each) → ManyOne/OneOne: single UPDATE extracting `->>'id'` with `NULLIF(…,'')` so empty strings become NULL → OneMany-on-table: explode array via LATERAL, dedup competing parents by MIN(self_id) (deterministic winner under one-to-many constraint), update only rows whose FK is still NULL → ManyMany/one-way-OneMany: INSERT DISTINCT pairs guarded by NOT EXISTS.
**Invariant:** Backfills are IDEMPOTENT and CONSERVATIVE — every arm writes only NULL/missing targets and never overwrites existing FKs; the MIN(self_id) tie-break exists because a one-to-many FK cannot hold two parents, so repair must choose deterministically rather than error.
**Probe:** `grep -cF 'jsonb_array_elements' apps/nestjs-backend/src/features/integrity/link-integrity.service.ts` → 2; `grep -cF 'MIN(self_id)' <same>` → 2; `grep -cF 'PRAGMA' <same>` → 2 (SQLite PRAGMA statements filtered out before execution at :640/:646).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "backfillForeignKeysFromLinkColumn jsonb_array_elements", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt conservative idempotent backfill + deterministic conflict resolution; adapt extraction functions to your JSON storage; omit the PRAGMA filter if your knex dialect emits none.
