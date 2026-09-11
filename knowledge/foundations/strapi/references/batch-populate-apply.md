<!-- capsule-v2 -->
# Batch populate apply — how do you populate one relation attribute across a whole result page with a single query and no N+1?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** How are many-to-many (and morph) relations attached to a page of rows in one round trip while preserving per-row grouping and join-table ordering?

## Batch populate seam
**Path/Symbol:** `packages/core/database/src/query/helpers/populate/apply.ts:manyToMany` (317–403); dispatcher `applyPopulate`/`populateAttribute` (721–784); sibling branches `XtoOne`, `oneToMany`, `manyToMany`, `morphX`, `morphToMany`, `morphToOne`.
**Signature:** `const manyToMany = async (input: InputWithTarget<Relation.ManyToMany>, ctx: Context) => void` — mutates `results[i][attributeName]` in place.
**Data Shape:** input `{ attribute, attributeName, results, populateValue, targetMeta, isCount }`; `attribute.joinTable = { name, joinColumn, inverseJoinColumn, on }`; rows are raw DB rows (`mapResults: false`).

### Decisive source
```ts
const referencedValues = _.uniq(results.map((r) => r[referencedColumnName]).filter((v) => !_.isNil(v)));
...
if (_.isEmpty(referencedValues)) {
  results.forEach((result) => { result[attributeName] = []; });   // [] not null
  return;
}
const rows = await populateQb
  .init(populateValue)
  .join({ alias, referencedTable: joinTable.name, referencedColumn: ..., orderBy: getJoinTableOrderBy(populateValue, joinTable) })
  .addSelect(joinColSelect)                       // `${alias}.${joinColumnName} as ${joinColRenameAs}`
  .where({ [joinColAlias]: referencedValues })    // one IN(...) query for the whole page
  .execute<Row[]>({ mapResults: false });

const map = _.groupBy<Row>(joinColRenameAs)(rows);
results.forEach((result) => {
  result[attributeName] = fromTargetRow(map[result[referencedColumnName] as string] || []);
});
```
Count mode replaces the fetch with `.select([joinColAlias, populateQb.raw('count(*) AS count')]).groupBy(joinColAlias)` and maps counts back, defaulting `{ count: 0 }`.

**Flow:** collect unique non-nil referenced ids from the page → early-return empty arrays/counts if none → one query against the *target* uid joined to the link table, filtered by the renamed link column → group rows in memory by that rename key → assign per source row via its own referenced value.
**Invariant:** The link column must be aliased with a dedicated prefix and selected under `mapResults: false` so it survives row mapping; missing groups become `[]` (never `undefined`/`null`) — this exact behavior is regression-pinned; join-table order drives list order.
**Probe:** `packages/core/database/src/query/helpers/populate/__tests__/apply-morph-many.test.ts` — "returns [] when an entry has no related morph rows" pins the empty-collection serialization for both morphToMany-join and morphToOne-inverse target branches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "populate apply rows target", file_pattern: "packages/core/database/src/query/helpers/populate/*", limit: 20 });
```
Executed during pass 1: 30 total matches led by `fromTargetRow` (670–671), `applyPopulate` (721–784), the six relation branches.

## Verdict
Adopt page-level id collection + single IN query + in-memory groupBy mapping as the N+1 killer, including the count variant. Adapt the alias/rename prefix scheme to your SQL builder's quoting rules. Omit Strapi's `joinTable.on` extra filters unless you have equivalent per-relation conditions. Coverage: `no_recorded_issue` + `metadata_match` for `apply.ts`.
