<!-- capsule-v2 -->
# Group-by execution fork — why can't every dialect GROUP BY the same query, and what shape does each take?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does one grouped-data-list implementation serve pg/mysql/sqlite AND MSSQL/Oracle whose SQL rules forbid the obvious form?

## Two shapes behind one API
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts:list` (:109-724, fork at :516-583) and `count` (:726-1124, fork at :1062-1120); shared helper `aliasDerivedTable` (:99-107).
**Signature:** `groupBy(baseModel, logger)` is a FACTORY returning `{ count, list }` closures sharing helpers; called from `BaseModelSqlv2.groupBy/groupByCount`.
**Data Shape:** Inner `qb` projects group-key expressions under stable aliases (`getAs(column)`); outer query references them as `g.<alias>`.

### Decisive source
```ts
// :516-523 — WHY the fork exists: MSSQL can't GROUP BY a select alias or a
// correlated subquery (rollup/lookup KEYS ARE correlated subqueries);
// oracle < 23c can't GROUP BY an alias (ORA-00904) and NO oracle version can
// GROUP BY a subquery-valued alias (ORA-22818). Only these two engines take
// the derived-table path; pg/mysql/sqlite group directly.
if (!baseModel.isMssql && !baseModel.isOracle) {
  qb.groupBy(...groupBySelectors);

// :391-395 — the inner COUNT is ALSO forked: pushing COUNT(*) into a
// projection that the outer table then groups against is "an aggregate with
// no GROUP BY" → ORA-00937 on Oracle. So mssql/oracle SKIP it here...
if (!baseModel.isMssql && !baseModel.isOracle) {
  qb.count(`${baseModel.model.primaryKey?.column_name || '*'} as count`);
}

// :549-561 — ...and count OUTSIDE instead:
//   SELECT count(*) [, subgroup COUNT(DISTINCT)] , <aliases>
//   FROM (<qb>) __nc_grp_src__ GROUP BY <aliases> [HAVING COUNT(*) >= min]
const grouped = baseModel.dbDriver
  .select(baseModel.dbDriver.raw(
    `count(*) as ??${subGroupCountSelect}${groupBySelectors.length ? `, ${aliasRefs.join(', ')}` : ''}`,
    ['count', ...subGroupCountBindings, ...aliasBindings]))
  .from(aliasDerivedTable(qb, '__nc_grp_src__'));

// :572-575 — BOTH engines end in WITH grouped AS (...) SELECT * FROM grouped g
// so the sort block can uniformly reference g.<alias>. But T-SQL FORBIDS
// wrapping a CTE in a derived table → the final __nc_group_alias wrap below
// must be skipped for mssql (and oracle, see :709-717: an UNQUOTED identifier
// can't start with '_' there → ORA-00911; knex's oracledb dialect already
// applies its own ROWNUM pagination wrapper, so execute directly).
outerQb = baseModel.dbDriver.with('grouped', grouped.clone())
  .select('*').from({ g: 'grouped' });
```
`aliasDerivedTable` (:99-107) delegates the `(sub) AS alias` syntax to `DBQueryClient.get(clientType).tableAlias` because **Oracle forbids `AS` on a TABLE alias** while the rest require it — never hand-write `(..) as t` around a subquery.

**Flow:** build inner projection + filters once → fork: direct `GROUP BY` aliases (pg/mysql/sqlite) vs derived-table regrouping (mssql/oracle) → uniform `WITH grouped … FROM grouped g` shell → optional final `__nc_group_alias` wrap (default path ONLY).
**Invariant:** (1) The same filter stack (view root filter, filterArr, xwhere, soft-delete) is applied BEFORE the fork, so both shapes select identical rows. (2) mssql/oracle move ALL aggregation outward — any new aggregate added to the inner query breaks them with ORA-00937. (3) The final derived-table wrap is default-path-only; adding pagination or ORDER BY after it silently changes nothing for mssql/oracle which already executed.
**Probe:** No unit tests upstream. Deterministic probe: clientType mssql ⇒ rendered SQL contains `__nc_grp_src__` and has NO inner `count(`; sqlite ⇒ contains `WITH grouped` and ends wrapped by `__nc_group_alias`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "groupBy", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.list Function group-by.ts 109-724
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.aliasDerivedTable Function group-by.ts 99-107
```

## Verdict
Adopt the two-shape fork with aggregation placement keyed to dialect limits, the tableAlias indirection, and the mssql/oracle no-wrap rule. Adapt queue of key expressions to your column system. Caveat: no direct tests at pin; graph ranges verified live.
