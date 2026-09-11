<!-- capsule-v2 -->
# populateMeta introspection spine — in what order does an external source become NocoDB metadata, and what must not run concurrently?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When a non-NocoDB database source is connected, what ordered funnel turns raw introspection into Model/Column/LTAR rows, and which phases are deliberately sequenced vs parallel?

## populateMeta introspection spine
**Path/Symbol:** `packages/nocodb/src/helpers/populateMeta.ts` — `populateMeta` (:244–665), phase calls at :569–571 (`NcHelp.executeOperations(tableMetasInsert)`, `executeOperations(virtualColumnsInsert)`, then `extractAndGenerateManyToManyRelations`).
**Signature:** `populateMeta(context, {source, base, logger?, user}) → Promise<{type:'rest', apiCount, tablesCount, relationsCount, viewsCount, client, timeTaken}>`.
**Data Shape:** `models2: {[tableName]: Model}` accumulates inserted Models keyed by physical table name; `virtualColumnsInsert: Array<() => Promise<void>>` defers LTAR inserts until every real column exists.

### Decisive source
```ts
// :284–294 — relations are read BEFORE tables and reused per-table:
let order = 1;
const models2: { [tableName: string]: Model } = {};
const virtualColumnsInsert = [];
/* Get all relations */
const relations = (
  await sqlClient.relationListAll({
    schema: getSourceIntrospectionSchema(source),
  })
)?.data?.list;
// :568–571 — three strictly ordered phases:
/* handle xc_tables update in parallel */
await NcHelp.executeOperations(tableMetasInsert, source.type);
await NcHelp.executeOperations(virtualColumnsInsert, source.type);
await extractAndGenerateManyToManyRelations(context, Object.values(models2));
```

**Flow:** (1) record dbVersion into `source.meta` when changed (non-meta sources only, best-effort catch); (2) `relationListAll` once for the whole schema; (3) `tableList` filtered by static `IGNORE_TABLES`, aliased via `getTableNameAlias(t.tn, base.prefix, source)`; prefix filter applied ONLY when `source.is_meta && base?.prefix`; (4) per-table closures built (columnList, hm/bt split by comparing `r.tn`/`r.rtn` to table name, virtual columns appended to deferred list); (5) `executeOperations` runs table closures through a PQueue (default concurrency 5 from `NC_EXECUTE_OPERATIONS_CONCURRENCY`) — so TABLES insert in parallel; (6) THEN virtual (LTAR) columns insert in a second queue wave — safe because every referenced `models2[rel.tn]` exists after wave 5; (7) only then mm extraction walks the completed models.
**Invariant:** Virtual-column inserts MUST run as a separate phase after all real columns of ALL tables exist — the deferred closure resolves `fk_child_column_id`/`fk_parent_column_id` by looking up sibling models' columns (`models2?.[rel.tn]?.getColumns(context)`); running waves concurrently or interleaved would resolve ids against half-built metadata. `NcHelp.executeOperations` (:11–41) additionally enforces stop-on-first-error: queued tasks check `if (errors.length) return` before executing, and the FIRST caught error is rethrown after `queue.onIdle()` — later tasks neither run nor report.
**Probe:** `grep -c "await NcHelp.executeOperations" packages/nocodb/src/helpers/populateMeta.ts` → `3` (tables, virtual columns, views waves).
**Coverage caveat:** no upstream unit spec covers populateMeta directly (bases/sources services call it at :413/:260); probe pins are grep-derived from source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "populateMeta executeOperations relationListAll", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-wave ordering (relations→tables→virtual links→views) and stop-on-first-error queue semantics; adapt the PQueue concurrency env knob and IGNORE_TABLES list to host naming; omit the apiCount bookkeeping arithmetic (5/table, 5/nested relation, 2/view — cosmetic stats). Views get their own wave at :640 with NO virtual columns (views never have relations), and grid views get `View.fixPVColumnForView` repair afterward (:648–655).
