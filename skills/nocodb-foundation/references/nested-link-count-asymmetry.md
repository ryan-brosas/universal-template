<!-- capsule-v2 -->
# Nested-link count-key asymmetry — why does hmList return `totalRows` while every sibling returns `count`?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When porting the five nested-link list methods, which response envelope differs and why is the difference load-bearing?

## DatasService nested list family
**Path/Symbol:** `packages/nocodb/src/services/datas.service.ts:mmList` (:645-725), `mmExcludedList` (:727-804), `hmExcludedList` (:806-883), `btExcludedList` (:885-964), `ooExcludedList` (:966-1074), `hmList` (:1076-1148).
**Signature:** All take `{ viewId, colId, query, rowId }`; each resolves view→model (`Model.getByIdOrName({ id: view?.fk_model_id || param.viewId })`) → source → fresh baseModel, then restricts the query (see nested-link-query-restriction), then runs data+count.
**Data Shape:** `nocoExecute(requestObj, {[key]: async (args) => baseModel.mmList(...)}, {}, { nested: { [key]: param.query } })` — a synthetic one-key AST whose resolver closure receives parsed nested args; key is `` `${model.title}List` `` for mm/hm but plain `'List'` for excluded variants.

### Decisive source
```ts
// hmList return (:1145-1147):
return new PagedResponseImpl(data, {
  totalRows: count,
} as any);                       // ← only hmList uses totalRows

// every sibling (:721-724 mm shown; same shape :800-803, :879-882, :960-963, :1070-1073):
return new PagedResponseImpl(data, {
  count,
  ...param.query,
});
```
```ts
// ooExcludedList dialect fork (:1012-1068): LinkV2 columns are served by the
if (isLinkV2(column)) {          // mm excluded-list primitives …
  data = ... baseModel.getMmChildrenExcludedList({ colId, pid: param.rowId }, args)
  count = await baseModel.getMmChildrenExcludedListCount(...)
} else {                         // … while classic oo has its own pair
  data = ... baseModel.getExcludedOneToOneChildrenList({ colId, cid: param.rowId }, args)
  count = await baseModel.countExcludedOneToOneChildren(...)
}
```

**Flow:** per method: resolve → restrict → synthetic-AST fetch + separate raw count call (the AST wraps ONLY the data fetch; count always goes to the dedicated `*Count` baseModel primitive with the same mutated query) → PagedResponse. Parameter naming drift across primitives is real and load-bearing: `mmList` takes `{colId, parentId}`, hm takes `{colId, id}`, bt/oo-classic take `{colId, cid}`; excluded-mm/oo-v2 take `{colId, pid}` — swapping them silently returns wrong/unlinked sets.
**Invariant:** The `totalRows` vs `count` split is a wire-contract difference consumed by different frontend generations — "fixing" it to be uniform breaks one client family. The synthetic-AST trick exists so nested where/sort inside `{nested:{[key]:query}}` applies to the linked rows without re-implementing arg parsing; the count path deliberately bypasses nocoExecute. Excluded lists share the identical restriction gate because their pkAndPvOnly projection makes hidden-column predicates a one-bit oracle over unlinked rows too.
**Probe:** Runner blocked at this pin. Deterministic probe: grep confirms exactly ONE `totalRows: count` in the file (:1146) and four `count,\n  ...param.query` envelopes; exactly one `isLinkV2(column)` fork.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "mmExcludedList getMmChildrenExcludedListCount", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the synthetic-one-key-AST pattern for nested collections and the dedicated-count-primitive pairing. Preserve per-family envelope keys verbatim if you serve both client generations; otherwise migrate atomically. Omit the LinkV2 fork if your port has no v2 link type.
