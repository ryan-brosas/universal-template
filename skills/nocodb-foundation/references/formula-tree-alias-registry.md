<!-- capsule-v2 -->
# formula tree alias registry — how does a formula column's field reference become SQL, and what does the compiler thread through every node?

**Source:** nocodb (Sustainable Use License) `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory `nocodb`. **Question:** What is the entry contract of the v2 formula compiler — what structure turns `{FieldRef}` identifiers into per-dialect SQL, and which context objects must a porter carry through recursion?

## formula tree alias registry
**Path/Symbol:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts:_formulaQueryBuilder` (:56–494) + `default formulaQueryBuilderv2` (:496–724).
**Signature:** `_formulaQueryBuilder(params: FormulaQueryBuilderBaseParams): Promise<{ builder: any; parsedTree? }>` where params = `{ baseModelSqlv2, _tree, model, aliasToColumn?, columnIdToUidt?, tableAlias, parsedTree?, column?, columns, parentColumns: CircularRefContext, getAliasCount: () => number, baseUsers? }`.
**Data Shape:** `aliasToColumn: Record<colId, ({tableAlias, parentColumns}) => Promise<{builder}>>` — a registry of LAZY builder factories keyed by column id, populated once per call for every column of the model (:127–374). The internal closure `fn(pt, prevBinaryOp?)` recurses over the jsep tree; `Identifier` nodes resolve via `aliasToColumn[pt.name]`.

### Decisive source
```ts
// :127–137 — registry seeding: EVERY column gets an entry before compilation
for (const col of columns) {
  columnIdToUidt[col.id] = col.uidt;
  if (col.id in aliasToColumn) continue;
  switch (col.uidt) {
    case UITypes.Formula:
    case UITypes.Button:
      aliasToColumn[col.id] = async ({ tableAlias, parentColumns }) => {
        parentColumns = (parentColumns ?? CircularRefContext.make()).cloneAndAdd({
          id: col.id, title: col.title, table: model.title });
        // recurse into the referenced formula; PRE-seed own id -> null
        const { builder } = await _formulaQueryBuilder({
          ..., aliasToColumn: { ...aliasToColumn, [col.id]: null }, ... });
        builder.sql = '(' + builder.sql + ')';   // nested formulas are paren-wrapped
        return { builder };
      };
```

**Flow:** wrapper `formulaQueryBuilderv2` → seeds `parentColumns` with the owning column (`cloneAndAdd` :540–546) and mints the shared `getAliasCount` monotonic counter (`formulaContext.count++` :529–535) → `_formulaQueryBuilder`: (1) parse `_tree` via SDK `validateFormulaAndExtractTreeWithType` unless a persisted `parsedTree` was supplied; legacy `{{ }}` normalized to `{ }` first (:82–86); (2) persist fresh parsed trees back to `FormulaColumn`/`ButtonColumn` FIRE-AND-FORGET (`update(...).then(ignore, log)` :102–123) — never awaited; (3) seed `aliasToColumn` per column uidt: Formula/Button → recursive builder; Lookup/LinkToAnotherRecord → `lookupOrLtarBuilder`; Rollup/Links (non-bt-like-v2) → inline `genRollupSelectv2` wrapped `( )`; Links that ARE `isBtLikeV2Junction` → routed to `lookupOrLtarBuilder` instead (:180–188); CreatedTime/LastModifiedTime/DateTime → tz-normalizing builders (mysql `CONVERT_TZ(??, @@GLOBAL.time_zone,'+00:00')` :218; pg non-timestamptz `AT TIME ZONE CURRENT_SETTING('timezone') AT TIME ZONE 'UTC'` :233; oracle TZ columns `SYS_EXTRACT_UTC(??)` :252; alias + refCol BOTH registered :260); User/CreatedBy/LastModifiedBy → lazy user-email REPLACE chain with memoized `BaseUser.getUsersList(..., {include_internal_user: true})` (:267–306); AI LongText → per-dialect JSON extraction (`TRIM('"' FROM (??::jsonb->>'value'))` pg / `JSON_UNQUOTE(JSON_EXTRACT(...))` mysql / `json_extract` sqlite / `JSON_VALUE` mssql :309–349); QrCode/Barcode → unwrapped to the referenced VALUE column (:350–363); default → `??.??` qualified name (:365–372). (4) `fn` walks the tree: CallExpression stamps `arg.fnName = parentCalleeName; arg.argsCount` onto arguments BEFORE building (:377–383) — this is how deferred aggregates later learn their parent function; `cast === STRING` wraps the subtree in a synthetic `STRING()` call (:386–398); Identifier → registry hit; a builder that comes back as a FUNCTION means "aggregate thunk, call me with the parent fnName" (:442–444). Function-name dispatch goes through `mapFunctionName.ts` (:21–54): `clientType → module table` (pg/mysql/sqlite/databricks/mssql/oracle), `val = table[name] || name` — a plain string REPLACES `pt.callee.name` (identity rename e.g. pg `LEN → 'length'`), a function receives the full `MapFnArgs` and takes over. NOTE the `'maridb'` case-label typo in mapFunctionName.ts :28 — harmless today because MariaDB connects via the `mysql2` driver, but do NOT "fix" it silently when porting; keep parity with upstream.
**Invariant:** (1) `aliasToColumn[col.id] = null` MUST be pre-seeded before recursing into a nested formula — it is the cycle-breaker that makes circular references throw `ERR_CIRCULAR_REF_IN_FORMULA` instead of infinite recursion. (2) `columnIdToUidt` must be filled for ALL columns before any binary expression compiles (date-literal handling reads it). (3) Nested formula SQL is parenthesized by MUTATING `builder.sql` after the fact — the wrap happens outside knex, so any port that re-wraps via `.wrap()` double-parenthesizes. (4) One shared `getAliasCount` counter names ALL generated aliases (`__nc_formulaN`, `__ncN`) across the whole statement — two counters produce colliding subquery aliases.
**Probe:** `packages/nocodb/src/db/formulav2/formulaQueryBuilderv2.ts` :127–168 (registry + nested wrap), :529–546 (counter + parentColumns seeding). Runner BLOCKED — no upstream unit tests for the db/ plane; verified by line-exact graph retrieval.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "_formulaQueryBuilder aliasToColumn CircularRefContext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy registry-of-builder-factories shape, the null-seed cycle breaker, shared alias counter, and fire-and-forget parsedTree persistence; adapt the per-uidt builder bodies to host column types; omit NestJS logger/telemetry wiring. Coverage caveat: behavior pinned at frozen pin f7513664f3f3; no upstream test suite covers this file.
