<!-- capsule-v2 -->
# Group-by RLS entry — row-level filters enter as filterArr, NEVER as a conditionV2 group

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** Where exactly do RLS policies inject into the grouped list/count paths, and why that shape?

## Prepend-into-filterArr at the BaseModelSqlv2 wrappers
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2.ts:groupBy` (:1263-1286) and `:groupByCount` (:1288-1308); consumption inside group-by.ts :486-495 / :1042-1051.
**Signature:** both wrappers clone `args` with `filterArr: [new Filter({ children: rlsConditions, is_group: true }), ...(args.filterArr || [])]`.
**Data Shape:** `getRlsConditions()` → Filter[] (dynamic `{currentUser.x}`-style conditions already resolved by the RLS seam mined in pass 10).

### Decisive source
```ts
// BaseModelSqlv2.ts :1263-1276 (groupBy; twin at :1288-1308):
async groupBy(args) {
  // Prepend RLS conditions to filterArr for groupBy
  const rlsConditionsGB = await this.getRlsConditions();
  if (rlsConditionsGB.length) {
    args = { ...args, filterArr: [
      new Filter({ children: rlsConditionsGB, is_group: true }),
      ...(args.filterArr || []),
    ]};
  }
  return await baseModelGroupBy(this, logger).list(args);
}
```

**Flow:** wrapper resolves RLS once → wraps into a single AND'd is_group Filter PREPENDED ahead of caller filterArr → the shared three-group stack inside group-by.ts applies view-root-filter + filterArr + xwhere via one conditionV2 call.
**Invariant:** (1) Prepend order = RLS evaluated FIRST among explicit filters; dropping it makes grouped counts leak rows outside policy scope. (2) RLS rides the SAME funnel as user filters here — unlike `groupByAndAggregate`, which builds a separate dedicated conditionV2 group. (3) Wrappers are the ONLY injection point: the group-by module itself never queries RLS.
**Probe:** No unit tests upstream. Deterministic probe: with a base role policy active, `groupBy()` args.filterArr[0].children === getRlsConditions() output; rendered SQL contains those conditions before user where-clauses.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getRlsConditions groupBy", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.BaseModelSqlv2.groupBy Method BaseModelSqlv2.ts 1263-1286
```

## Verdict
Adopt wrapper-level prepend-into-filterArr for grouped reads. Adapt Filter model to host. Caveat: no direct tests at pin; graph range verified live.
