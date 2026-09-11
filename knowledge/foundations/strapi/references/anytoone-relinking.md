<!-- capsule-v2 -->
# AnyToOne relinking — how do you swap an exclusive polymorphic link without destroying sibling locale/draft documents' links?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** When entity A's `anyToOne` field is re-pointed to B', which old link rows are safe to delete, and how do you avoid deleting the rows that belong to *other documents of the same target* (other locales, draft/publication variants)?

## Exclusive-relation relink seam
**Path/Symbol:** `packages/core/database/src/entity-manager/regular-relations.ts:deletePreviousAnyToOneRelations` (99–161); exclusion source `getDocumentSiblingIdsQuery` (27–55).
**Signature:** `const deletePreviousAnyToOneRelations = async ({ id, attribute, relIdToadd, db, transaction }: {...}) => Promise<void>`.
**Data Shape:** operates on `attribute.joinTable` `{ name, joinColumn (owner side), inverseJoinColumn (target side) }`; `relIdToadd` is the incoming target row id; `joinTable.on` carries optional per-relation extra filters.

### Decisive source
```ts
// handling manyToOne: if the database integrity was not broken relsToDelete is supposed to be of length 1
const relsToDelete = await con
  .select(inverseJoinColumn.name)
  .from(joinTable.name)
  .where(joinColumn.name, id)
  .whereNotIn(
    inverseJoinColumn.name,
    getDocumentSiblingIdsQuery(inverseJoinColumn.referencedTable!, relIdToadd)
  )
  .where(joinTable.on || {})
  .transacting(trx);
...
await cleanOrderColumns({ attribute, db, inverseRelIds: relIdsToDelete, transaction: trx });
```
The oneToOne branch performs the same `DELETE ... WHERE joinColumn = id AND inverseJoinColumn NOT IN (documentSiblingIds)` directly.

**Flow:** assert the attribute really is anyToOne → compute the ids that must be spared via the sibling query (rows in the target's table sharing the incoming document's `documentId` but differing locale/status) → select stale inverse-join ids excluding siblings → delete exactly those join rows inside the caller's transaction → for manyToOne also clean order columns of the deleted ids.
**Invariant:** Deletion scope is always `NOT IN (documentSiblingIds(newTarget))` + `joinTable.on` filters; the operation runs under the caller-supplied transaction (`transacting(trx)`), never its own; comment pins the expectation "relsToDelete is supposed to be of length 1" when integrity holds.
**Probe:** No unit test isolates this helper in-tree; behavior is covered by relation API integration suites (`tests/api/core/database/db.test.api.js` exercises relation connect semantics). Caveat recorded: probe strength here is integration-level, not a direct unit test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "regular relations connect delete links", qn_pattern: ".*regular-relations.*", limit: 25 });
```
Executed during pass 1: surfaced `deletePreviousAnyToOneRelations` (99–161), `deletePreviousOneToAnyRelations` (60–94), `deleteRelations` (166–234), `cleanOrderColumns` (239–382).

## Verdict
Adopt the document-sibling exclusion predicate as the general rule for exclusive-link replacement in any system where one logical document has multiple physical rows (locales, versions, drafts). Adapt what "sibling" means to your host's variant columns. Omit Strapi's `documentId` model and order-column cleanup if your join tables are unordered. Coverage: `no_recorded_issue` + `metadata_match` for `regular-relations.ts`.
