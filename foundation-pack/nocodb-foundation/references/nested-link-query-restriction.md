<!-- capsule-v2 -->
# Nested-link query restriction — why must the strip run BEFORE both fetch and count, and why is view-`show` NOT the gate?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When a linked table's rows are listed through a link column, which caller-supplied query parts are legal, and when must they be rewritten?

## restrictNestedLinkQuery family
**Path/Symbol:** `packages/nocodb/src/helpers/nestedLinkQueryHelpers.ts:restrictNestedLinkQuery` (:219-298), `restrictQueryToExposedColumns` (:300-365), `restrictNestedLinkQueryForColumn` (:368-389). Call sites: every nested method of `datas.service.ts` (`mmList` :682, `mmExcludedList` :761, `hmExcludedList` :840, `btExcludedList` :921, `ooExcludedList` :1002, `hmList` :1107).
**Signature:** `restrictNestedLinkQuery(context, colOptions: LinkToAnotherRecordColumn, relatedModel: Model, query, options?: { hasLimitedAccess?: boolean })`; the Column-holding wrapper no-ops for non-LTAR columns.
**Data Shape:** `query` (where/sort aliases from `LIST_ARG_ALIASES.where|.sort`) is MUTATED IN PLACE — comment: "Mutates `param.query`, which both the data fetch and the count read from" (datas.service.ts :679-681).

### Decisive source
```ts
// datas.service.ts mmList :654-660 — the DESIGN NOTE quoted verbatim:
// NOTE: view-hidden columns stay queryable here and in the sibling
// nested-link methods below — field visibility is the column-level ACL,
// not view `show`, so we do NOT strip where/sort just because a column is
// hidden in the view (see the DESIGN NOTE in public-datas.service.ts).
// The `restrictNestedLinkQueryForColumn` calls below are a SEPARATE
// boundary: they gate on cross-base / no-visibility-access related tables,
// not on view `show`.
```
```ts
// nestedLinkQueryHelpers.ts :251-262 — the three-way gate ladder
const restricted =
  isSharedViewAccess(context) ||                       // ALWAYS restrict; checked first so a
                                                       // caller's hasLimitedAccess:false can't override
  (options?.hasLimitedAccess !== undefined
    ? options.hasLimitedAccess                          // EE optimized SELECT threads its own decision —
                                                        // predicate and SELECT can't disagree
    : colOptions.isCrossBaseLink() ||
      !(await hasTableVisibilityAccess(context, relatedModel.id, context.user)));
if (!restricted) return;
// exposed set = pk + pv + the link's custom display column (:270-277)
const exposedColumnIds = new Set(
  columns.filter((c) => c.pk || c.pv || c.id === displayValueColId).map((c) => c.id),
);
```
```ts
// restrictQueryToExposedColumns :316-330 — alias-totality + leaf-level surgery
// EVERY alias spelling present is rewritten, not just the one `getListArgs`
// would pick: sanitizing only the current winner would let a change to that
// precedence promote an untouched alias into the compiler.
//
// An unresolvable reference is LEFT ALONE: it resolves to nothing downstream,
// and dropping it would change the error behaviour of malformed queries.
```

**Flow:** entry → non-LTAR/absent-query no-op → early return unless BOTH where and sort absent-skip → compute restricted via ladder → resolve related-table columns in the link's OWN refContext into a LOCAL list ("don't mutate the shared model's column cache", :264-269) → exposed = {pk, pv, display} → parse xwhere, drop only offending leaves, re-serialize survivors ONLY if something was actually hidden (fast guard `filtersReferenceHiddenColumn`), else leave original string untouched → sanitize sort terms → same mutated query feeds fetch AND count.
**Invariant:** (1) Strip-before-both-consumers: count and data read the SAME object, so sanitizing after either would leak via the unsanitized one. (2) The gate dimension is cross-base/visibility ACL — never view `show`; conflating them breaks grid UX for hidden-but-queryable fields. (3) Empty-group pruning, not whole-where deletion: "dropping the whole `where` would turn a multi-field search into 'return every record'" (:334-335) — a fail-OPEN disaster. (4) Unresolvable references stay (fail toward existing error behavior). (5) Excluded-list variants share the identical restriction because their pkAndPvOnly projection makes a hidden-column predicate the same one-bit oracle over UNLINKED rows (:754-759).
**Probe:** Runner blocked at this pin. Deterministic probe: grep counts 5 `restrictNestedLinkQueryForColumn` call sites + 1 direct `restrictNestedLinkQuery`-shaped call in datas.service.ts; helpers file contains exactly one `pk || c.pv || c.id === displayValueColId` exposure triple.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "restrictNestedLinkQueryForColumn exposedColumnIds", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: single shared sanitizer, mutate-once-before-both-consumers, leaf-level strip with group pruning, exposure = pk+pv+display. Adapt the access ladder to your auth model. Omit the `hasLimitedAccess` threading if you have no optimized-SELECT path — but then keep the conservative default.
