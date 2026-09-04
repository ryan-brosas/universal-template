<!-- capsule-v2 -->
# Composite Sub-Field Filter Compilation — how does `{fullName: {firstName: {ilike: ...}}}` become a flat column condition?

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `twenty-crm`. **Question:** How are composite field types (fullName, emails, phones, address, links) flattened into their physical sub-columns for filtering — and what is the exact column-naming algebra?

## name + Capitalized(subFieldKey) flattening over composite type definitions
**Path/Symbol:** `packages/twenty-server/src/engine/api/graphql/graphql-query-runner/graphql-query-parsers/graphql-query-filter/graphql-query-filter-field.parser.ts` : `GraphqlQueryFilterFieldParser.parseCompositeFieldForFilter` (lines 224–283).
**Signature:** `parseCompositeFieldForFilter(queryBuilder: WhereExpressionBuilder, fieldMetadata: FlatFieldMetadata, objectNameSingular: string, fieldValue: any, isFirst = false, useDirectTableReference = false): void`.
**Data Shape:** `fieldValue` is `{ [subFieldKey]: { [operator]: value } }`; the composite definition (`compositeTypeDefinitions.get(fieldMetadata.type)`) supplies `.properties[] = { name, ... }`; each sub-field compiles independently and all are ANDed.

### Decisive source
```ts
const compositeType = compositeTypeDefinitions.get(
  fieldMetadata.type as CompositeFieldMetadataType,
);

if (!compositeType) {
  throw new Error(`Composite type definition not found for type: ${fieldMetadata.type}`);
}

Object.entries(fieldValue).map(([subFieldKey, subFieldFilter], index) => {
  const subFieldMetadata = compositeType.properties.find(
    (property) => property.name === subFieldKey,
  );

  if (!subFieldMetadata) {
    throw new Error(`Sub field metadata not found for composite type: ${fieldMetadata.type}`);
  }

  const fullFieldName = `${fieldMetadata.name}${capitalize(subFieldKey)}`;

  const [[operator, value]] = Object.entries(subFieldFilter as Record<string, any>);

  assertArrayOperatorValueIsNonEmptyArray({ operator, value, key: subFieldKey });

  const { sql, params } = computeWhereConditionParts({
    operator, objectNameSingular,
    key: fullFieldName,
    subFieldKey,
    value,
    fieldMetadataType: fieldMetadata.type,
    useDirectTableReference,
  });

  if (isFirst && index === 0) {
    queryBuilder.where(sql, params);
  }

  queryBuilder.andWhere(sql, params);
});
```

**Flow:** look up composite definition → per submitted sub-field: validate against `properties`, derive physical column as `fieldName + Capitalized(subFieldKey)` (so `fullName.firstName` → column `"fullNameFirstName"`, quoted as `"person"."fullNameFirstName"` by the SQL ladder), destructure exactly one operator entry (the `[[operator, value]]` destructure silently drops extra operator keys — first-wins), guard array operators, compile, AND-chain.
**Invariant:** every sub-field of a composite filter must resolve to a declared property or the request throws; unknown sub-fields never reach SQL. The naming algebra is load-bearing end-to-end: GraphQL input key → camelCase property → Capitalized concatenation → physical column name.
**Known quirk (source-confirmed, untested upstream):** when `isFirst && index === 0`, BOTH `.where(sql)` and the unconditional `.andWhere(sql)` execute — the first sub-condition is emitted twice in the bracket. Semantically idempotent per row (P AND P ≡ P) but produces duplicated SQL; no spec covers this path (condition-parser spec uses scalar fields only). Porters should emit once.
**Probe:** direct source read this pass of lines 224–283; coverage caveat recorded above. RUNNER BLOCKED (jest unavailable).

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "twenty-crm", query: "parseCompositeFieldForFilter composite type definition sub field full name capitalize", limit: 6, fields: ["signature"] });
// → parseCompositeFieldForFilter 224-283 (rank 3); FullNameMetadata composite type (rank 1)
```

## Verdict
Adopt the capitalize-concatenation naming algebra and validate-and-throw on unknown sub-fields. Adopt the one-operator-per-sub-field first-wins destructure ONLY with an explicit decision — silent dropping is upstream's behavior but not a safe default. Adapt to your storage layout (upstream stores composites flattened into real columns, which is what makes this compile to plain comparisons instead of JSON accessors). Fix the double-emit when porting.
