<!-- capsule-v2 -->
# Filter Field Permission Gates — what runs before SQL compilation so a filtered query denies loudly instead of leaking rows?

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `twenty-crm`. **Question:** When a user filters on a field their role cannot read — or an object they cannot read at all — where in the filter compiler does the deny happen, and is it a throw or a no-row predicate?

## Deny-before-SQL gate ladder in the per-field parser
**Path/Symbol:** `packages/twenty-server/src/engine/api/graphql/graphql-query-runner/graphql-query-parsers/graphql-query-filter/graphql-query-filter-field.parser.ts` : `GraphqlQueryFilterFieldParser.parse` (lines 62–143), with key resolution in `utils/resolve-filter-key-field-metadata.util.ts` (lines 7–34).
**Signature:** `parse(queryBuilder: WhereExpressionBuilder, outerQueryBuilder: RecordQueryBuilder, objectNameSingular: string, key: string, filterValue: any, isFirst = false, useDirectTableReference = false): void`.
**Data Shape:** permissions ride ON the query builder (`outerQueryBuilder.objectRecordsPermissions[objectMetadataId]`), not on a separate context object; field maps (`fieldIdByName`, `fieldIdByJoinColumnName`) are built once per parser from flat metadata.

### Decisive source
```ts
const { fieldMetadata, isReferencedByFieldName } =
  resolveFilterKeyFieldMetadata({
    filterKey: key,
    fieldIdByName: this.fieldIdByName,
    fieldIdByJoinColumnName: this.fieldIdByJoinColumnName,
    flatFieldMetadataMaps: this.flatFieldMetadataMaps,
  });

if (!isDefined(fieldMetadata)) {
  throw new Error(`Field metadata not found for field: ${key}`);
}

const objectPermissions =
  outerQueryBuilder.objectRecordsPermissions[this.flatObjectMetadata.id];

if (objectPermissions?.canReadObjectRecords === false) {
  throw new PermissionsException(
    PermissionsExceptionMessage.PERMISSION_DENIED,
    PermissionsExceptionCode.PERMISSION_DENIED,
  );
}

assertFieldIsReadableOrThrow({
  objectsPermissions: outerQueryBuilder.objectRecordsPermissions,
  objectMetadataId: this.flatObjectMetadata.id,
  fieldMetadataId: fieldMetadata.id,
});
// ...only then: dispatch to relation / composite / scalar compilation
```

**Flow:** resolve filter key (field-name map first, join-column-name map fallback — e.g. filtering `companyId` resolves to the `company` relation field) → unknown key throws plain Error → object-level read deny throws PERMISSION_DENIED → field-level readability assert throws → only then compile SQL. Note the fail-open asymmetry: `canReadObjectRecords === false` is checked strictly, but an *absent* permission entry (`undefined`) passes.
**Invariant:** permission checks execute BEFORE any SQL string exists — a denied filter is a loud GraphQL error, never a silently-empty result set and never compiled SQL that could leak through another code path. Strict-`false` + undefined-passes keeps queries working for roles with no explicit row-permission rows.
**Probe:** direct source read of `graphql-query-filter-field.parser.ts:80–98` this pass (assertion order). The dedicated spec covers the condition walker, not these gates — coverage caveat: gate behavior pinned by source order only; RUNNER BLOCKED (jest unavailable in checkout).

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "twenty-crm", query: "GraphqlQueryFilterFieldParser parse permission denied field readable filter key metadata", limit: 6, fields: ["signature"] });
// → GraphqlQueryFilterFieldParser.parse 62-143, parseCompositeFieldForFilter 224-283,
//   parseRelationSubFilter 145-222, resolveFilterKeyFieldMetadata 7-34
```

## Verdict
Adopt gates-before-compilation with strict-deny-on-explicit-false semantics and join-column key resolution as an accessibility nicety. Adapt the permission carrier to your framework (query-builder-attached maps are a TypeORM-ism). Omit the plain `Error` for unknown fields if your API contract needs typed error codes — upstream uses an untyped throw here (asymmetry vs the typed `GraphqlQueryRunnerException` used deeper in the same file).
