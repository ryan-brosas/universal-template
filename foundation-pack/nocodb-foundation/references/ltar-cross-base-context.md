<!-- capsule-v2 -->
# Cross-base link context resolution — how does a link column address tables that live in ANOTHER base without leaking permissions?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When a link (or its junction table) lives in a different base, how are the four contexts (related/junction/parent/child) derived, and which context field must be dropped and why?

## LinkToAnotherRecordColumn.getRelContext / getParentChildContext
**Path/Symbol:** `packages/nocodb/src/models/LinkToAnotherRecordColumn.ts:getRelContext` (:314-360), `getParentChildContext` (:362-417), `isCrossBaseLink` (:419-425), plus the accessor family `getRelatedTable/getMMModel/getMMChildColumn/getMMParentColumn` (:96-220), `getChildView` (:260-273).
**Signature:** `getRelContext(context: NcContext): { refContext: NcContext; mmContext: NcContext }` — MEMOIZED on the instance (`this._context`).
**Data Shape:** Cross-base columns carry their own routing ids: `fk_related_base_id`, `fk_mm_base_id`, `fk_related_source_id`, `fk_mm_source_id` (null for same-base links). Contexts differ from the caller's ONLY in base_id + permissions.

### Decisive source
```ts
// if the related table is in different base
if (this.fk_related_base_id && this.fk_related_base_id !== context.base_id) {
  refContext = {
    ...context,
    base_id: this.fk_related_base_id,
    // `permissions` is base-scoped (the request base's, preloaded by
    // middleware). Drop it so visibility checks against the related table
    // resolve the related base's own permissions instead of silently
    // inheriting the request base's — otherwise a cross-base
    // TABLE_VISIBILITY restriction is read against the wrong base, finds no
    // matching rule, and defaults to accessible (leaking the related table).
    permissions: undefined,
  };
}
```
```ts
public async getMMModel(context: NcContext, ncMeta = Noco.ncMeta): Promise<Model> {
  // Resolve mmContext relative to THIS link's own base (like getRelatedTable /
  // getMMChildColumn), not the caller's context. Otherwise a caller passing a
  // different base (e.g. a cross-base lookup chain) plus a same-base junction
  // (fk_mm_base_id null) would resolve the junction model in the wrong base
  // and miss it.
  const { mmContext } = this.getRelContext({ ...context, base_id: this.base_id });
```
```ts
async getParentChildContext(context, column?, ncMeta) {
  ...
  if (isMMOrMMLike(col)) parentContext = refContext;      // v2 om/mo/mm: junction-based, parent always related-side
  else if (this.type === RelationTypes.HAS_MANY) childContext = refContext;   // hm: FK column lives on related table
  else if (this.type === RelationTypes.BELONGS_TO) parentContext = refContext;
  else if (this.type === RelationTypes.ONE_TO_ONE) {
    if (col?.meta?.bt) parentContext = refContext; else childContext = refContext;  // oo: whichever side holds the FK
  }
```

**Flow:** every accessor re-bases onto `{...context, base_id: this.base_id}` BEFORE calling getRelContext (so a cross-base caller chain still resolves the link's own relatives) → getRelContext memoizes refContext/mmContext once per instance → getParentChildContext additionally splits parent/child contexts by relation type → cacheMap is propagated to all derived contexts (request-scoped cache coherence survives re-basing).
- `getChildView`: explicit `fk_target_view_id` wins; otherwise fallback is `View.getFirstCollaborativeView` — deliberately NOT raw index-0 view, "which is unordered and can be another user's personal view."
**Invariant:** (1) `permissions: undefined` on EVERY re-based context is load-bearing — inheriting the request base's permissions defaults cross-base visibility checks to accessible (a leak). (2) Accessors must resolve relative to the LINK's own base id, not whatever base the caller came from. (3) Memoization means one instance must never be reused across requests with different bases.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `LinkToAnotherRecordColumn.getRelContext` :314-360 exactly; grep confirms exactly two `permissions: undefined` sites (:336, :346) and one `getFirstCollaborativeView` fallback (:272).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getRelContext refContext mmContext fk_related_base_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the memoized four-context derivation with permission-dropping on re-base and link-owned-base accessor resolution. Adapt NcContext shape (workspace/base/source triple) to your tenancy object. Omit oo's meta.bt side-detection only if you have no one-to-one flavor.
