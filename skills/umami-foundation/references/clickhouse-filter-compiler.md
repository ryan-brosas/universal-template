<!-- capsule-v2 -->
# ClickHouse filter compiler — how do you turn a JSON filter bag into safe, parameterized CH SQL (incl. cohort joins and property filters)?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How is user-controlled filtering compiled into ClickHouse SQL without injection and with correct AND/OR semantics?

## clickhouse-filter-compiler
**Path/Symbol:** `src/lib/clickhouse.ts:mapFilter :84-110, getFilterQuery :112-151, getCohortQuery :153-175, getExcludeBounceQuery :177-197, getDateQuery :210-232, parseFilters :239-265, getPropertyFilterQuery :268-462`.
**Signature:** `parseFilters(filters, options?) -> { filterQuery, dateQuery, queryParams, cohortQuery, excludeBounceQuery }` — string fragments spliced into query templates; values ALWAYS as `{param:Type}` bind placeholders.
**Data Shape:** filters bag `Record<name, value|operator.value>`; `FILTER_COLUMNS` whitelist maps names→columns (unknown names produce NO column ⇒ silently skipped).

### Decisive source
```ts
function mapFilter(column, operator, name, type = 'String', paramName?) {
  const value = `{${param ?? name}:${type}}`;                       // typed placeholder
  switch (operator) {
    case OPERATORS.equals:      return `${column} IN {${param}:Array(${type})}`;
    case OPERATORS.contains:    return `positionCaseInsensitive(${column}, ${value}) > 0`;
    case OPERATORS.regex:       return `match(${column}, concat('(?i)', ${value}))`;
    ...
  }
}
// eventType and the cohort action are STRUCTURALLY required to be ANDed even in 'any' mode:
const isAlwaysAnd = name === 'eventType' || (isCohort && name === cohortActionName);
```

**Flow:** filtersObjectToArray → per-filter mapFilter into and/or clause buckets → OR-group wrapped `(a\nor b)` prepended before AND clauses → cohort/bounce sub-joins appended separately → params flattened by paramName.
**Invariant:** only whitelisted FILTER_COLUMNS ever reach SQL text — user input lives exclusively in `{p:Type}` placeholders. The always-AND set (`eventType`, cohort action) exists because OR-of-filters must not let an `any` match bypass the event-type or cohort-membership constraint — dropping it makes cohort counts wrong, not just different.
**Probe:** `grep -c "toMatchObject" src/lib/clickhouse.test.ts` → 1 (:5 pins utc/second/minute formats; the `%i`-unsupported comment at clickhouse.ts:6-8 explains token choices).
**Probe:** `grep -c "positionCaseInsensitive" src/lib/clickhouse.ts` → ≥4 lines.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "mapFilter getFilterQuery cohort excludeBounce", limit: 10 });
```

## Verdict
Adopt the whitelist-column + typed-placeholder fragment compiler for any dynamic-SQL analytics API; adapt operator vocabulary; port the always-AND concept anywhere "OR within a constrained scope" queries exist.
