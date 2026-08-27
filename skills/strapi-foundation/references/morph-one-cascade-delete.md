<!-- capsule-v2 -->
# MorphOne cascade delete — how do you keep exclusive morphOne links consistent when a morphToMany collection is rewritten?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** A `morphMany`/`morphOne` pair shares one join table; when the many-side collection is replaced, which rows must be deleted so no exclusive one-side link points at a row that no longer exists — and how do ids from different types stay unambiguous?

## Morph cascade seam
**Path/Symbol:** `packages/core/database/src/entity-manager/morph-relations.ts:deleteRelatedMorphOneRelationsAfterMorphToManyUpdate` (lines 39–89), `getMorphToManyRowsLinkedToMorphOne` (11–37), `encodePolymorphicId` (98–100), `encodePolymorphicRelation` (102–120); call sites in `packages/core/database/src/entity-manager/index.ts` at 685–693 (set/connect path), 1066–1072 (disconnect path), 1141–1147 (set path).
**Signature:** `deleteRelatedMorphOneRelationsAfterMorphToManyUpdate(rows, { uid, attributeName, joinTable, db, transaction }): Promise<void>`; `encodePolymorphicId(id, __type): string` → `` `${id}:::${__type}` ``.
**Data Shape:** `rows` are the INCOMING morphToMany join rows (`{ [joinColumn]: id, [idColumn]: targetId, [typeColumn]: targetUid, field?, order? }`); the join table's `morphColumn` carries `idColumn` + `typeColumn`; deletion is one `$or`-grouped DELETE.

### Decisive source
```ts
// keep only incoming rows that point back at a morphOne inverse of THIS morphToMany
const targetAttribute = db.metadata.get(relatedType).attributes[field] as Relation.MorphOne;

return (
  targetAttribute?.target === uid &&
  targetAttribute?.morphBy === attributeName &&
  targetAttribute?.relation === 'morphOne'
);
```
```ts
// group by (type, field), then ONE delete with an $or of {type, field, id IN [...]}
const typeAndFieldIdsGrouped = pipe(groupByType, mapValues(groupByField))(morphOneRows);

for (const [type, v] of Object.entries(typeAndFieldIdsGrouped)) {
  for (const [field, arr] of Object.entries(v)) {
    orWhere.push({
      [typeColumn.name]: type,
      field,
      [idColumn.name]: { $in: map(idColumn.name, arr) },
    });
  }
}

if (!isEmpty(orWhere)) {
  await createQueryBuilder(joinTable.name, db)
    .delete()
    .where({ $or: orWhere })
    .transacting(trx)
    .execute();
}
```
```ts
// entity-manager/index.ts — cascade runs BEFORE the new rows are inserted, same transaction
await deleteRelatedMorphOneRelationsAfterMorphToManyUpdate(rows as any, {
  uid, attributeName, joinTable, db, transaction: trx,
});

await batchInsertJoinTable(db, joinTable.name, rows, trx);
```

**Flow:** the write pipeline builds the new morphToMany rows (join column = owner id, id/type columns from each entry, `order` assigned by the relations orderer over ENCODED ids) → the cascade scans those incoming rows and keeps only ones whose `(type, field)` resolves in metadata to a `morphOne` attribute with `target === uid` AND `morphBy === attributeName` (i.e. the exclusive inverse of this very relation) → groups kept rows by type then field → issues a single `DELETE ... WHERE ($or [{type, field, id IN [...]}])` inside the caller's transaction → the fresh rows are batch-inserted after. The same helper is invoked on all three rewrite paths (set-before-connect, disconnect-with-deletes, plain set).
**Invariant:** the cascade deletes based on the INCOMING rows, not the old table contents — it removes stale exclusive links whose targets are being re-pointed, while leaving links owned by other morphMany attributes untouched; it must run before the insert and in the same transaction so the pair is atomic; an empty group set short-circuits (no no-op DELETE); polymorphic identity is always the encoded `${id}:::${__type}` pair — raw numeric ids from different types can collide, so the orderer and dedup logic must never see bare ids.
**Probe:** `tests/api/core/strapi/document-service/relations/polymorphic.test.api.ts` (morphToOne/morphMany/morphToMany round-trips through the document service; header documents why these tests avoid wrapping writes in the test's own Knex transaction — pool deadlock on SQLite) plus `tests/api/core/strapi/document-service/delete-morph-join-order.test.api.ts` (manyToMany declared before morphToMany in attribute order — join-write ordering regression).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "deleteRelatedMorphOneRelationsAfterMorphToManyUpdate encodePolymorphicId", file_pattern: "packages/core/database/src/entity-manager/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 3 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the reverse-link cascade pattern for any shared join table backing an exclusive/inclusive polymorphic pair: derive deletions from the incoming dataset, group by (type, field) into one `$or` DELETE, run before insert in the same transaction. Adopt encoded composite ids (`id:::type`) wherever two types share one id space. Adapt the metadata lookup (`target`/`morphBy` match) to your relation model. Omit Strapi's `__pivot`/`joinTable.on` extras unless you port pivot columns. Coverage caveat: no unit test exists for `morph-relations.ts`; the contract is pinned by document-service API tests read this pass.
