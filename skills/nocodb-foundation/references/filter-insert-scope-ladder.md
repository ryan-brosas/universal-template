<!-- capsule-v2 -->
# Filter.insert — which FK scope resolves source_id, and when is `order` caller-owned?

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3b7286023a7e832a8333808f7557b`; Codebase Memory project `nocodb`. **Question:** When porting filter creation, how do you derive `source_id` for a filter attached to any of seven scopes (view/hook/link-col/parent-col/button/level/column), and when may the caller own `order`?

## The scope→model ladder + replay-keep-order
**Path/Symbol:** `packages/nocodb/src/models/Filter.ts:Filter.insert` (:145-265).
**Signature:** `static async insert(context: NcContext, filter: Partial<FilterType & { meta?: any | string }>, ncMeta = Noco.ncMeta)`.
**Data Shape:** extractProps allowlist of 22 keys (`id`, all seven scope FKs, `comparison_op/sub_op`, `value`, `fk_parent_id`, `is_group`, `logical_op`, `base_id`, `source_id`, `order`, `meta`, `enabled`). `referencedModelColName` = FIRST present among `[fk_parent_column_id, fk_view_id, fk_hook_id, fk_row_color_condition_id, fk_link_col_id, fk_rls_policy_id, fk_button_col_id]`.

### Decisive source
```ts
// packages/nocodb/src/models/Filter.ts:184-189 — caller owns order ONLY under replay
const replayKeepOrder = isReplay() && filter.order != null;
if (!replayKeepOrder) {
  insertObj.order = await ncMeta.metaGetNextOrder(MetaTable.FILTER_EXP, {
    [referencedModelColName]: filter[referencedModelColName],
  });
}
// :191-232 — source_id derived by scope ladder; fallthrough ends in NcError.invalidFilter
if (!filter.source_id) {
  if (filter.fk_view_id && !filter.fk_parent_column_id) {
    model = await View.get(context, filter.fk_view_id, false, ncMeta);
  } else if (filter.fk_hook_id) { ... }        // Hook.get
  else if (filter.fk_link_col_id) { ... }      // Column.get
  else if (filter.fk_parent_column_id) { ... } // Column.get
  else if (filter.fk_button_col_id) { ... }    // Column.get
  else if (filter.fk_column_id) { ... }        // Column.get
  else if (filter.fk_level_id) { /* ListViewLevel.get → level.fk_model_id */ }
  else { NcError.invalidFilter(JSON.stringify(filter)); }
}
// :249-262 — children recurse with parent's id AND the SAME scope key re-stamped
await Promise.all(filter.children.map((f) =>
  this.insert(context, { ...f, fk_parent_id: row.id,
    [referencedModelColName]: filter[referencedModelColName] }, ncMeta)));
```

**Flow:** extractProps allowlist → compute `order` via `metaGetNextOrder` scoped to the first-present scope column (unless replay with explicit order) → resolve `source_id` through the seven-way ladder (view branch EXPLICITLY yields when `fk_parent_column_id` also set) → stringify meta → `metaInsert2(FILTER_EXP)` → parallel child recursion carrying `fk_parent_id` + same scope key → `redisPostInsert`.
**Invariant:** every FILTER_EXP row must carry a resolvable `source_id`; children must be stamped with the ROOT's scope key so the whole tree lands under one cache scope; caller-supplied `order` is honored only inside command-replay (`isReplay()`) — undo→redo round-trips need stable orders.
**Probe:** No direct unit test at this pin. Deterministic probes: verbatim greps for `replayKeepOrder` (:184) and `metaGetNextOrder(MetaTable.FILTER_EXP` (:186); `search_graph --project nocodb --query 'Filter.insert'` resolves `models.Filter.Filter.insert … Filter.ts 145-265`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "Filter.insert metaGetNextOrder referencedModelColName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: one insert path serving every filter consumer via a first-match scope ladder that also keys per-scope ordering; recursion re-stamps the root's scope key on children; replay-only order preservation. Adapt the scope-key list to whichever filter surfaces your host has. Omit: EE-specific consumers (`fk_row_color_condition_id`, `fk_widget_id` appear only in the allowlist). Coverage caveat: no runner exercises this file at this pin (construction-only spec culture); evidence is line-pinned source + graph resolution.
