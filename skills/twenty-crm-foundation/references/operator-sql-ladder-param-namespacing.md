<!-- capsule-v2 -->
# Operator→SQL Ladder with Random Param Namespacing — how does one function emit parameterized SQL for ~18 filter operators without collisions?

**Source:** twenty-crm AGPL-3.0 `main@9e4717278c29efa3ba0c147f6acf0d68e99a625c`; Codebase Memory `twenty-crm`. **Question:** How are GraphQL filter operators (`eq`, `in`, `ilike`, `contains`, `search`, array operators…) compiled into safe parameterized Postgres, and how do multiple conditions on the SAME field coexist in one params bag?

## Per-condition random param suffix + quoted qualified field reference
**Path/Symbol:** `packages/twenty-server/src/engine/api/graphql/graphql-query-runner/utils/compute-where-condition-parts.ts` : `computeWhereConditionParts` (lines 20–215).
**Signature:** `computeWhereConditionParts({ operator, objectNameSingular, key, subFieldKey?, value, fieldMetadataType, useDirectTableReference? = false }): { sql: string; params: ObjectLiteral }`.
**Data Shape:** returns a raw SQL fragment plus a params object keyed `${key}${hexSuffix}` (and a second suffixed key when null-equivalence adds an OR arm). Field reference is `"object"."key"` or, under `useDirectTableReference` (mutation queries), bare `"key"`.

### Decisive source
```ts
const paramSuffix = randomBytes(5).toString('hex');
const secondParamSuffix = randomBytes(5).toString('hex');

const fieldReference = useDirectTableReference
  ? `"${key}"`
  : `"${objectNameSingular}"."${key}"`;

const isDateTimeField = fieldMetadataType === FieldMetadataType.DATE_TIME;

switch (operator) {
  case 'eq':
    if (isDateTimeField) {
      return {
        sql: `(${fieldReference} >= :${key}${paramSuffix} AND ${fieldReference} < :${key}${paramSuffix}::timestamptz + interval '1 millisecond')...`,
        params: { [`${key}${paramSuffix}`]: value },
      };
    }
    return { sql: `${fieldReference} = :${key}${paramSuffix}...`, ... };
  case 'in':
    return { sql: `${fieldReference} IN (:...${key}${paramSuffix})`, ... };
  case 'startsWith':
    return { sql: `${fieldReference}::text ^@ :${key}${paramSuffix}`, ... };
  case 'endsWith':
    return { sql: `RIGHT(${fieldReference}::text, LENGTH(:${key}${paramSuffix})) = :${key}${paramSuffix}`, ... };
  case 'contains':
    return { sql: `${fieldReference} @> ARRAY[:...${key}${paramSuffix}]`, ... };
  case 'search': {
    const tsQuery = formatSearchTerms(value, 'and');
    return { sql: `(${fieldReference} @@ to_tsquery('simple', public.unaccent_immutable(:${key}${paramSuffix}Ts)) OR public.unaccent_immutable(${fieldReference}::text) ILIKE ...)`, ... };
  }
  case 'containsIlike':
    return { sql: `EXISTS (SELECT 1 FROM unnest(${fieldReference}) AS elem WHERE elem ILIKE :...)`, ... };
  default:
    throw new GraphqlQueryRunnerException(
      `Operator "${operator}" is not supported`,
      GraphqlQueryRunnerExceptionCode.UNSUPPORTED_OPERATOR,
      { userFriendlyMessage: STANDARD_ERROR_MESSAGE },   // generic; no operator echo
    );
}
```

**Flow:** suffix params → build field reference (alias-qualified vs direct) → dispatch on operator string → DATE_TIME equality/range operators get ±1ms windows around `::timestamptz + interval '1 millisecond'` (millisecond storage precision makes plain `=` lossy across offsets) → text ops cast `::text`; startsWith uses PG `^@`, endsWith uses RIGHT/LENGTH, array membership uses `@>`/`&&`/`unnest EXISTS`, search combines tsquery + unaccented ILIKE fallback → unknown operator throws typed UNSUPPORTED_OPERATOR with a generic user-facing message.
**Invariant:** every bound value is a numbered/suffixed parameter — no value is ever stringified into SQL. Param keys must be unique per condition even when several conditions target the same column in one query (hence cryptographic suffixes, not counters).
**Probe:** direct source read this pass of lines 20–215. No dedicated unit spec found for this util via graph search (`compute-where-condition-parts.*spec*` total:0) and glob over the package's `__tests__` dirs lists no match — coverage caveat: behavior pinned by source only; RUNNER BLOCKED (jest unavailable).

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "twenty-crm", query: "computeWhereConditionParts operator sql params random suffix timestamptz", limit: 6, fields: ["signature"] });
// → computeWhereConditionParts packages/twenty-server/src/engine/api/graphql/graphql-query-runner/utils/compute-where-condition-parts.ts 20-215 (rank 1)
```

## Verdict
Adopt: per-condition randomized param namespacing, alias-vs-direct field-reference switch for read vs mutation SQL, ms-window datetime equality, generic-message failure for unknown operators. Adapt operator spellings/PG-specific syntax (`^@`, `@>`, `unaccent_immutable`) to your dialect. Omit the tsvector+ILIKE dual-arm search if you have a dedicated search index.
