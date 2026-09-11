<!-- capsule-v2 -->
# User-column group sort — resolving user IDs to display names INSIDE SQL, per dialect

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you sort grouped rows by a User/CreatedBy/LastModifiedBy column's display name when the stored value is only a user id?

## REPLACE-chain / CASE-map translation of the grouped key
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts:list` :595-661.
**Signature:** branch entered for `UITypes.User | CreatedBy | LastModifiedBy` group keys; builds `finalStatement` then orders by it.
**Data Shape:** roster from `BaseUser.getUsersList({ base_id, include_internal_user: true })` mapped as `id → display_name || email`.

### Decisive source
```ts
// :604-609 — the ALREADY-GROUPED key is read off the outer alias g.<col> and
// blank-normalized (isStringType: true — the key is text here):
const groupedColQb = sqlNullIfBlank({ columnName: raw('??.??', ['g', getAs(column)]),
                                      baseModel, isStringType: true });

// :611-624 — pg/sqlite translate via the shared client helper (a keyed
// CASE/DECODE-style map over the whole roster):
finalStatement = `(${DBQueryClient.get(clientType).replaceDelimitedWithKeyValue({
  knex, needleColumn: groupedColQb,
  stack: baseUsers.map((user) => ({ key: user.id, value: user.display_name || user.email }))})})`;

// :625-633 — everyone else: FOLDED nested REPLACE(acc, ?, ?) per roster entry,
// each layer bound with parameters and materialized via .toQuery():
const qbReplace = raw(`REPLACE(${acc}, ?, ?)`, [user.id, user.display_name || user.email]);
return qbReplace.toQuery();
```
Direction handling reuses the same count-sort/MSSQL-bucket/default NULLS ladder as ordinary keys (:634-661).

**Flow:** detect user-family column → load base-user roster once → build id→display-name expression over `g.<alias>` → feed into the same three-branch ORDER BY emission.
**Invariant:** (1) Translation happens on the OUTER query against the grouped alias — never re-aggregates or joins users. (2) The REPLACE-chain is order-sensitive only in appearance: ids are replaced atomically, so overlapping prefixes are safe; but a port that swaps arguments breaks every mapping. (3) Roster is loaded ONCE per sort, not per row.
**Probe:** No unit tests upstream. Deterministic probe: pg SQL contains `CASE`/map construct around `g."Title"` while mysql shows nested `REPLACE(REPLACE(g.`...`,'id1','Name'),...)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "replaceDelimitedWithKeyValue BaseUser getUsersList", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.list Function group-by.ts 109-724 (:595-661)
```

## Verdict
Adopt outer-key id→display-name translation with the two dialect strategies. Adapt roster source to host. Caveat: no direct tests at pin; graph range verified live.
