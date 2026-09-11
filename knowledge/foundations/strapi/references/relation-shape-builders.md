<!-- capsule-v2 -->
# Relation shape builders — how do you derive which side of a relation owns storage and which storage shape each relation kind gets, without a configuration matrix?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Relations can be stored as a join column on the owner row, a pivot join table, or polymorphic columns — and either side of a bidirectional pair must agree. How do you decide ownership and storage shape per relation kind, and how do the two sides stay consistent?

## Relation-shape seam
**Path/Symbol:** `packages/core/database/src/metadata/relations.ts` (whole file, 649 lines): `createRelation` dispatch (622–649), `createOneToOne` (88–106), `createOneToMany` (114–129), `createManyToOne` (146–169), `createManyToMany` (181–194), `createMorphToOne` (204–219), `createMorphToMany` (221–334), `createJoinColumn` (389–407), `createJoinTable` (412–620); predicates `isOwner` (60–63), `shouldUseJoinTable` (65–67), `isAnyToMany`/`isManyToAny` (49–56), `isBidirectional` (57–59).
**Signature:** `createRelation(attributeName: string, attribute: RelationalAttribute, meta: Meta, metadata: Metadata): void` — mutates `attribute` in place (adds `owner`, `joinColumn` or `joinTable`) and may `metadata.add(...)` a new join-table Meta.
**Data Shape:** ownership is DERIVED, never declared: `isOwner = !isBidirectional(attr) || hasInversedBy(attr)` — the side declaring `inversedBy` owns; `mappedBy` marks the inverse. `shouldUseJoinTable = !('useJoinTable' in attr) || attr.useJoinTable !== false`.

### Decisive source
```ts
// ownership derivation: the inversedBy side owns; mappedBy is the mirror
const isOwner = (attribute: RelationalAttribute): attribute is RelationalAttribute & Relation.Owner =>
  !isBidirectional(attribute) || hasInversedBy(attribute);
const shouldUseJoinTable = (attribute: RelationalAttribute) =>
  !('useJoinTable' in attribute) || attribute.useJoinTable !== false;
```
```ts
// oneToMany: join table ONLY when unidirectional; a bidirectional owner side is a hard error
if (shouldUseJoinTable(attribute) && !isBidirectional(attribute)) {
  createJoinTable(metadata, { attribute, attributeName, meta });
} else if (isOwner(attribute)) {
  throw new Error('one side of a oneToMany cannot be the owner side in a bidirectional relation');
}
```
```ts
// manyToOne: the many side MUST own
if (isBidirectional(attribute) && !isOwner(attribute)) {
  throw new Error('The many side of a manyToOne must be the owning side');
}
```
```ts
// self-reference disambiguation: both sides derive the same column name, so rename the inverse
if (joinColumnName === inverseJoinColumnName) {
  inverseJoinColumnName = identifiers.getInverseJoinColumnAttributeIdName(snakeCase(targetMeta.singularName));
}
if (attribute.relation === 'manyToMany' && orderColumnName === inverseOrderColumnName) {
  inverseOrderColumnName = identifiers.getInverseOrderColumnName(snakeCase(meta.singularName));
}
```
```ts
// inverse side backfill: mirrored joinTable descriptor with swapped columns
inverseAttribute.joinTable = {
  __internal__: true,
  name: joinTableName,
  joinColumn: joinTable.inverseJoinColumn,
  inverseJoinColumn: joinTable.joinColumn,
  pivotColumns: joinTable.pivotColumns,
};
```

**Flow:** `createRelation` switches on `attribute.relation` → oneToOne: owner + join table (unless `useJoinTable:false`) else join column; inverse side gets a mirrored `joinColumn` (name = referencedColumn, referencedColumn = joinColumnName) → oneToMany: join table only if unidirectional; bidirectional owner side throws → manyToOne: many side must own (throws otherwise); join table or join column → manyToMany: join table created only by the owner (unidirectional always creates) → morphToOne: attribute gains `owner:true` + `morphColumn {typeColumn, idColumn}` names derived from identifiers → morphToMany: builds a pivot Meta with a SINGLE FK to the owner table (CASCADE), `id/type/field/order` columns, three indexes, `__internal__:true` marker, and explicit `columnName` on the join column so the identifier shortener does not re-shorten an already-shortened name → `createJoinTable` adds order columns for anyToMany (`orderColumnName`) and bidirectional manyToAny (`inverseOrderColumnName`), a unique (join,inverse) index, CASCADE FKs both sides, then backfills the inverse attribute's joinTable descriptor with swapped columns and crossed order-column names.
**Invariant:** exactly one side of a bidirectional pair creates storage — the other receives a mirrored descriptor pointing at the SAME table, so both sides resolve to one physical structure; ownership must be derivable from the attribute alone (inversedBy vs mappedBy) because metadata loads models in arbitrary order; self-referencing relations must never emit two identically-named columns; `__internal__` join tables are re-derivable and are skipped on reload (`if (attribute.joinTable && !attribute.joinTable.__internal__) return`); the explicit `columnName` on pivot columns prevents double identifier shortening across passes.
**Probe:** `packages/core/database/src/metadata/__tests__/metadata.test.ts` 'relation conversion' error cases (136–245): missing target uid → `Metadata for "admin::role" not found`; unknown relation kind → `Unknown relation`; inversedBy pointing at a missing attribute → `inversedBy attribute permissions not found target ...`; inversedBy pointing at a non-relation attribute → `targets non relational attribute in ...`; duplicate table name gate. Join-table naming pinned by `metadata/__tests__/identifiers.test.ts` metadata snapshots (morphToMany expected results at 128–129).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "createRelation createJoinTable isOwner inversedBy joinColumn", file_pattern: "packages/core/database/src/metadata/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 6 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the ownership-derivation rule (inversedBy owns), the per-kind dispatch table with hard errors for impossible shapes (bidirectional oneToMany owner, non-owning many side), the mirrored-inverse joinTable descriptor, and the self-reference column renames. Adopt the `__internal__` re-derivation skip and explicit columnName to keep identifier shortening idempotent. Adapt the relation-kind set and identifier naming functions to your schema model. Omit Strapi's specific UID handling and the entity-service integration.
