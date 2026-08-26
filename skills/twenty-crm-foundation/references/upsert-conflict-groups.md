<!-- capsule-v2 -->
# upsert-conflict-groups — How does upsert decide which columns make two records "the same record"?

**Source:** twenty-crm (AGPL-3.0 — patterns only, never verbatim), main@a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0; Codebase Memory `ext-twenty-crm`. **Question:** How are conflict keys derived from metadata (id + unique indexes) into comparable property groups?

## upsert-conflict-groups
**Path/Symbol:** `packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/get-conflicting-fields.util.ts:getConflictingFields` (:128-172).
**Signature:** `(flatObjectMetadata: FlatObjectMetadata, flatFieldMetadataMaps: FlatEntityMaps<FlatFieldMetadata>, flatIndexMaps: FlatEntityMaps<FlatIndexMetadata>): ConflictingFieldGroup[]` where a group is `{ baseFields: string[], conflictingProperties: {fullPath, column}[] }`.
**Data Shape:** groups are derived purely from the workspace's cached metadata maps (no DB round-trip): the `id` field always becomes group #1; every index with `isUnique === true` becomes one more group.

### Decisive source
```ts
if (isMorphOrRelationFlatFieldMetadata(flatFieldMetadata)) {
  if (flatFieldMetadata.settings?.relationType !== RelationType.MANY_TO_ONE) {
    return undefined;   // has-many / many-to-many members DISQUALIFY the whole index
  }
  const joinColumn = computeMorphOrRelationFieldJoinColumnName({ name: flatFieldMetadata.name });
  return [{ fullPath: joinColumn, column: joinColumn }];
}
```
(:30-40; composite fields expand only their `isIncludedInUniqueConstraint` sub-properties :69-77.)

**Flow:** collect `id` group → iterate `flatObjectMetadata.indexMetadataIds` resolved through `flatIndexMaps`, filtering `isUnique` → per index, sort member fields by `order` → map each field to conflicting properties via three cases: MANY_TO_ONE relation ⇒ its FK join column; composite type ⇒ each unique-constraint sub-property as `field.subfield` full path with computed column name; scalar ⇒ identity. **Any unresolvable case returns `undefined` and the ENTIRE index is skipped** (:105-116, :152-163) — an unusable key degrades to "no conflict detection on that index", never to a wrong match.
**Invariant:** conflict semantics must equal the DB's actual UNIQUE constraints. That is why relation fields other than MANY_TO_ONE poison their index (their values live in junction tables, not this row) and why composite expansion is restricted to `isIncludedInUniqueConstraint` properties — matching anything broader would update records the unique index does not actually cover.
**Probe:** `grep -c 'isIncludedInUniqueConstraint' packages/twenty-server/src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/get-conflicting-fields.util.ts` → 1; direct spec: `src/engine/api/common/common-query-runners/common-create-many-query-runner/utils/__tests__/get-conflicting-fields.util.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-twenty-crm", query: "getConflictingFields unique index", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "conflict keys are exactly id + unique-index projections, derived from cached metadata, with fail-silent skip of any index whose projection cannot be materialized." Adapt the projection rules to your schema model (here: flat entity maps + composite column-name computation). Omit Twenty's specific field-type taxonomy but keep the disqualification rule for non-FK relation members.
