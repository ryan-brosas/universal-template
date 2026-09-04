<!-- capsule-v2 -->
# groupByAndAggregate dispatch — reflection-gated aggregate functions on a raw column_name

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does NocoDB expose "avg(price) per category" safely when the function name arrives from the client?

## qb[aggregateFn] capability check
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2.BaseModelSqlv2.groupByAndAggregate` (BaseModelSqlv2.ts :1185-1261).
**Signature:** `(aggregateColumnName: string, aggregateFn: string, args { where?, limit?, offset?, sortBy?, groupByColumnName? })`.
**Data Shape:** output column aliased `${fn}__${column}`; NO virtual-column compilation, NO CTE shell.

### Decisive source
```ts
// :1204-1210 — the whole security/robustness contract: the function name must
// be a METHOD ON THE KNEX BUILDER or it's rejected — no SQL fragment ever
// interpolates from client input:
const aggregateStatement = `${aggregateColumnName} as ${aggregateFn}__${aggregateColumnName}`;
if (typeof qb[aggregateFn] === 'function') {
  qb[aggregateFn](aggregateStatement);
} else {
  throw new Error(`Unsupported aggregate function: ${aggregateFn}`);
}

// :1214+ — plain select of the group column + standard filter stack:
qb.select(args.groupByColumnName);
const rlsConditionsGBA = await this.getRlsConditions();
const rlsFilterGroupGBA = rlsConditionsGBA.length
  ? [new Filter({ children: rlsConditionsGBA, is_group: true })] : [];
await conditionV2(this, [...rlsFilterGroupGBA,
  new Filter({ children: filterObj, is_group: true, logical_op: 'and' })], qb);
```
Then soft-delete filter, optional `groupBy(args.groupByColumnName)` + orderBy + applyPaginate + execAndParse — all on ONE flat query.

**Flow:** validate fn against builder methods → build `${col} as ${fn}__${col}` → flat select/group/filter/paginate.
**Invariant:** (1) Capability-check-by-reflection means knex version upgrades silently expand the accepted fn set — porters should keep an allowlist if that's unacceptable. (2) Unlike groupBy(), this path takes RAW column names and skips processColumn — virtual columns are out of scope here. (3) RLS enters as its own dedicated conditionV2 group (contrast: groupBy/groupByCount prepend into filterArr).
**Probe:** No unit tests upstream. Deterministic probe: `groupByAndAggregate('price','DROP','...')` throws `Unsupported aggregate function: DROP`; `'sum'` renders `select sum(price as sum__price)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "groupByAndAggregate", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.BaseModelSqlv2.groupByAndAggregate Method BaseModelSqlv2.ts 1185-1261
```

## Verdict
Adopt the reflection gate + flat-query shape for trusted-schema aggregate dashboards; add an allowlist if untrusted callers reach it. Caveat: no direct tests at pin; graph range verified live.
