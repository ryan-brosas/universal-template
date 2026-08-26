<!-- capsule-v2 -->
# UPDATE ... FROM SELECT with before-image self-join — how do you recompute columns in bulk AND capture old values for change events in one statement?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does one generated UPDATE return both new and pre-update column values (plus version) without a second query or triggers?

## UpdateFromSelectBuilder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/UpdateFromSelectBuilder.ts` — `buildWithReturning` splice (:246–289), alias helpers (:100–106), `prepareUpdateProjectionContext` (:292+), dirty-filter INNER JOIN application (`applyDirtyFilter`, type :27–37); direct tests `__tests__/UpdateFromSelectBuilder.spec.ts`.
**Signature:** `builder.build({table, fieldIds, selectQuery, tableAlias?, selectAlias?, recordFilter?, dirtyFilter?}): Result<{compiled, columnToFieldId, oldColumnAliases?}, DomainError>`.
**Data Shape:** Compiled Kysely query + mapping of physical column→fieldId + map of column→`__old_*` alias; returning row = `{__id, __old_version, [__old_<col>, <col>]...}`.

### Decisive source
```ts
const compiled = query.compile();
const whereIndex = compiled.sql.lastIndexOf(' where ');
if (whereIndex === -1) {
  return err(domainError.validation({
    message: 'UpdateFromSelect returning query is missing WHERE clause',
  }));
}
const sqlWithOldTable =
  compiled.sql.slice(0, whereIndex) +
  `, ${quoteQualifiedTableName(tableName)} as "${oldTableAlias}"` +
  compiled.sql.slice(whereIndex, whereIndex + ' where '.length) +
  `${quoteRef(oldTableAlias, '__id')} = ${quoteRef(selectAlias, '__id')} and ` +
  compiled.sql.slice(whereIndex + ' where '.length);
```

**Flow:** build the normal UPDATE...FROM SELECT via Kysely → to capture before-images, splice a second reference to the target table aliased `__old` into the FROM list and add an equality join on `__id` into the WHERE → append RETURNING of new columns plus `__old.col AS "__old_col"` plus the pre-update `__version` → the dirty temp-table filter is applied as an INNER JOIN "for better query planning" (spec :464). A missing WHERE clause is a hard validation error: without it the self-join would cross-join every row.
**Invariant:** The splice point MUST be the LAST ' where ' occurrence (Kysely may emit subquery-WHEREs), and the builder refuses to emit a WHERE-less update. Duplicate fields sharing one physical column collapse to a single SET (spec :302), errored fields sharing a healthy column defer to the healthy definition (:331), and `__version` increments inside the same statement unless the chunk is externally versioned (:410).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/UpdateFromSelectBuilder.spec.ts` (:221 base build, :302 shared-column single SET, :362 __version increment, :387 no-op when all fields skipped, :464 dirty INNER JOIN, :597 __old_version returned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "UpdateFromSelectBuilder buildWithReturning dirtyFilter", limit: 10 });
```

## Verdict
Adopt the self-join before-image splice with fail-closed WHERE guard and single-statement bulk recompute; adapt the alias names and projection plan to host schema; omit Kysely-specific compile/splice mechanics if your query builder can express UPDATE...FROM natively.
