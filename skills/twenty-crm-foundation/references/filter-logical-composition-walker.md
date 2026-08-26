<!-- capsule-v2 -->
# Filter Logical Composition Walker — how do and/or/not filters compose into TypeORM brackets without clobbering outer wheres?

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `twenty-crm`. **Question:** How does a recursive `{and|or|not, field}` filter tree become nested TypeORM brackets where the first entry uses `.where()` and every later one `.andWhere()` — without `.where()`'s replace semantics destroying outer conditions?

## Recursive bracket walk over filter entries
**Path/Symbol:** `packages/twenty-server/src/engine/api/graphql/graphql-query-runner/graphql-query-parsers/utils/apply-filter-entries-to-where-expression.util.ts` : `applyFilterEntriesToWhereExpression` / `applyFilterEntry` / `applyLogicalGroup` / `applyCondition` (lines 13–128).
**Signature:** `applyFilterEntriesToWhereExpression({ whereExpression: WhereExpressionBuilder; outerQueryBuilder: RecordQueryBuilder; objectNameSingular: string; filter: Record<string, unknown>; fieldParser: GraphqlQueryFilterFieldParser; useDirectTableReference?: boolean }): void`.
**Data Shape:** `filter` is the raw GraphQL `ObjectRecordFilter` plain object; reserved keys `and`, `or`, `not`; everything else dispatches to the field parser. Context carries the OUTER query builder because relation sub-filters must add joins to it while conditions attach to the inner bracket.

### Decisive source
```ts
const applyLogicalGroup = (
  whereExpression: WhereExpressionBuilder,
  filters: Record<string, unknown>[] | Record<string, unknown>,
  logicalOperator: 'and' | 'or',
  isFirst: boolean,
  context: FilterWalkContext,
): void => {
  const filterList = Array.isArray(filters) ? filters : [filters];

  const groupCondition = new Brackets((groupWhereExpression) => {
    filterList.forEach((filter, index) => {
      const elementCondition = new Brackets((elementWhereExpression) => {
        applyFilterEntries(elementWhereExpression, filter, context);
      });

      if (index === 0) {
        groupWhereExpression.where(elementCondition);
      } else if (logicalOperator === 'or') {
        groupWhereExpression.orWhere(elementCondition);
      } else {
        groupWhereExpression.andWhere(elementCondition);
      }
    });
  });

  applyCondition(whereExpression, groupCondition, isFirst);
};

const applyCondition = (...) => {
  if (isFirst) { whereExpression.where(condition); } else { whereExpression.andWhere(condition); }
};
```

**Flow:** top-level `GraphqlQueryFilterConditionParser.parse` wraps the whole filter in ONE `Brackets` → walk entries in insertion order → `and`/`or`: each list element gets its own child bracket (first element `.where`, rest `.andWhere`/`.orWhere`) → `not`: a single `NotBrackets` wrapping a recursive walk → leaf keys: field parser emits raw SQL into the current bracket → first entry of ANY bracket level uses `.where()` (TypeORM replaces), all later entries `.andWhere()`.
**Invariant:** `.where()`'s replace-once behavior is safe only because every recursion level owns a fresh bracket; the outermost parse-level bracket absorbs the single reset. An or-group given as a bare object must behave identically to `[object]` (normalization before iteration).
**Probe:** `graphql-query-runner/graphql-query-parsers/graphql-query-filter/__tests__/graphql-query-filter-condition.parser.spec.ts` — pins `where`→`andWhere` for two scalar entries, byte-equal trees for `or:` object vs `[object]` (lines 191–221), `notBrackets` shape (223–240), nested `and>or>not` tree (259–312), and empty-filter emitting zero calls (314–316). RUNNER BLOCKED: jest not executable in this checkout (no node_modules); verified by direct read of these assertions.

## Get live surrounding code
**Retrieve:** executed live this pass (`search_graph` BM25, returned the util at rank 3):
```ts
await mcp.codebase_memory.search_graph({ project: "twenty-crm", query: "applyFilterEntriesToWhereExpression logical and or not brackets walk", limit: 6, fields: ["signature"] });
// → ...graphql-query-parsers.utils.apply-filter-entries-to-where-expression.util.applyFilterEntriesToWhereExpression
//   packages/twenty-server/src/engine/api/graphql/graphql-query-runner/graphql-query-parsers/utils/apply-filter-entries-to-where-expression.util.ts 13-34
```

## Verdict
Adopt the fresh-bracket-per-level + isFirst-where discipline for any user-supplied boolean filter tree compiled onto a shared query builder. Adopt bare-object or-group normalization. Adapt bracket primitives to your ORM (Drizzle/Prisma need explicit parenthesization nodes). Omit the `outerQueryBuilder` threading unless your relation strategy adds joins during filter compilation.
