<!-- capsule-v2 -->
# Relation Sub-Filter Join Compiler — how do `{company: {name: {ilike: ...}}}` filters compile, and what bounds their nesting?

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `twenty-crm`. **Question:** Does a nested relation filter become a correlated subquery or a join on the outer query — and how is runaway recursion and duplicate-join risk handled?

## MANY_TO_ONE sub-filters as idempotent leftJoins + depth-capped child parser
**Path/Symbol:** `packages/twenty-server/src/engine/api/graphql/graphql-query-runner/graphql-query-parsers/graphql-query-filter/graphql-query-filter-field.parser.ts` : `GraphqlQueryFilterFieldParser.parseRelationSubFilter` (lines 145–222) + `utils/add-relation-join-alias.util.ts` : `addRelationJoinAliasToQueryBuilder` (lines 9–23).
**Signature:** `parseRelationSubFilter(queryBuilder: WhereExpressionBuilder, outerQueryBuilder: RecordQueryBuilder, parentAlias: string, fieldMetadata: FlatFieldMetadata, filterValue: Partial<ObjectRecordFilter>, isFirst: boolean): void`; `addRelationJoinAliasToQueryBuilder({ queryBuilder, parentAlias, relationName }): void`.
**Data Shape:** entered only when the key resolved via field-name (not join column) AND `fieldMetadata.settings.relationType === RelationType.MANY_TO_ONE`; child parser reuses the SAME flatFieldMetadataMaps but swaps target object metadata; `depth` travels in constructor state.

### Decisive source
```ts
if (this.depth >= MAX_RELATION_FILTER_DEPTH) {
  throw new GraphqlQueryRunnerException(
    `Relation filter nesting deeper than ${MAX_RELATION_FILTER_DEPTH} hop is not supported`,
    GraphqlQueryRunnerExceptionCode.INVALID_QUERY_INPUT,
    { userFriendlyMessage: msg`Relation filters can only traverse one relation deep` },
  );
}
// ...target-object existence checks with typed INVALID_QUERY_INPUT throws...

const joinAlias = fieldMetadata.name;

addRelationJoinAliasToQueryBuilder({
  queryBuilder: outerQueryBuilder,
  parentAlias,
  relationName: joinAlias,
});

const childConditionParser = new GraphqlQueryFilterConditionParser(
  targetObjectMetadata, this.flatFieldMetadataMaps,
  this.flatObjectMetadataMaps, this.depth + 1,
);

const subBrackets = new Brackets((subQb) => {
  childConditionParser.applyFilterEntriesToWhereBrackets(
    subQb, outerQueryBuilder, joinAlias, filterValue,
  );
});
```
and the idempotent join:
```ts
const alreadyJoined = queryBuilder.expressionMap.joinAttributes.some(
  (joinAttribute) => joinAttribute.alias.name === relationName,
);
if (alreadyJoined) return;
queryBuilder.leftJoin(`${parentAlias}.${relationName}`, relationName);
```

**Flow:** depth guard (MAX_RELATION_FILTER_DEPTH = **1**, `max-relation-filter-depth.constant.ts`) → require object-maps + relationTargetObjectMetadataId (typed throws with userFriendlyMessage) → resolve target object from flat maps → add leftJoin to the OUTER builder (alias = field name; skip if an alias of that name already exists in `expressionMap.joinAttributes`) → child ConditionParser(depth+1) compiles the sub-filter into a bracket where every column reference uses the JOIN ALIAS as its "objectNameSingular" (`"company"."name"`).
**Invariant:** sub-filter conditions must reference the joined alias, never the parent table alias — the child parser achieves this by treating the join alias AS the object name. The join lives on the outer query so ORDER BY/SELECT can share it; duplicate joins are prevented by alias-name scan, making repeated filters on the same relation safe. Depth cap converts unbounded recursion into a typed client error.
**Probe:** direct source read this pass of `graphql-query-filter-field.parser.ts:145–222`, `add-relation-join-alias.util.ts:14–22`, `max-relation-filter-depth.constant.ts:1`; coverage caveat: no dedicated spec pins the relation path (the condition-parser spec uses scalar fields only). RUNNER BLOCKED (jest unavailable).

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "twenty-crm", query: "parseRelationSubFilter relation filter depth join alias many to one", limit: 6, fields: ["signature"] });
// → addRelationJoinAliasToQueryBuilder 9-23 (rank 1), parseRelationSubFilter 145-222 (rank 3)
```

## Verdict
Adopt join-based MANY_TO_ONE compilation with alias-as-object-name child parsing, alias-scan idempotence, and a hard hop cap exposed as a user-friendly error. Adapt to ONE_TO_MANY/many-to-many needs (upstream deliberately does not support them here). Omit correlated EXISTS subqueries unless your engine cannot share joins with ORDER BY.
