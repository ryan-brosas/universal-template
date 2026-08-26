<!-- capsule-v2 -->
# system-column roster — what is the canonical set of columns every NocoDB-managed table carries and which are optional?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Which system columns does NocoDB add to tables it creates, how do flags gate the meta column, and what does `allowNonSystem` mean for user-facing column creation?

## system-column roster
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `TableSystemColumns(isMetaColSupport = false, isMeta = true)` (:773–838); consumed by table-create paths; complements `populateMeta.ts` NC_SYSTEM_COL_UIDT (:342–349).
**Signature:** returns array of `{column_name, title, uidt, allowNonSystem, system}`.
**Data Shape:** id (ID, system:false), created_at (CreatedTime, system:true), updated_at (LastModifiedTime), created_by (CreatedBy; title 'nc_created_by'), updated_by (LastModifiedBy; 'nc_updated_by'), nc_order (Order), __nc_deleted (Deleted) gated by `isMeta`, META_COL_NAME (Meta) gated by `isMetaColSupport`.

### Decisive source
```ts
// :773–780 + :816–837:
export const TableSystemColumns = (isMetaColSupport = false, isMeta = true) => [
  { column_name: 'id', title: 'Id', uidt: UITypes.ID,
    allowNonSystem: false, system: false },
  { column_name: 'created_at', ... allowNonSystem: true, system: true },
  ...
  ...(isMeta ? [{ column_name: '__nc_deleted', uidt: UITypes.Deleted,
                  allowNonSystem: false, system: true }] : []),
  ...(isMetaColSupport ? [{ column_name: META_COL_NAME, uidt: UITypes.Meta,
                  allowNonSystem: false, system: true }] : []),
];
```

**Flow:** table creation spreads this roster into DDL → `allowNonSystem: true` on time/user columns means a USER may also create their own column with that physical name without colliding with the system role (the roster entry then stays hidden); id/nc_order/__nc_deleted/meta are reserved (`allowNonSystem: false`). The soft-delete marker rides `__nc_deleted` only when the source supports meta columns (`isMeta`).
**Invariant:** The roster is the WRITE-side truth while populateMeta's six-name map is the READ-back recognition truth — they must agree on physical names for round-trips to re-identify NocoDB tables. Note asymmetries: titles for created_by/updated_by differ from column_names ('nc_created_by'), and `id` has system:false because it's exposed as a normal visible field despite being reserved.
**Probe:** `grep -c "allowNonSystem" packages/nocodb/src/helpers/columnHelpers.ts` → `8`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "TableSystemColumns META_COL_NAME", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the seven-entry roster + two boolean gates as one unit; keep write-roster/read-map name parity in any port; adapt Deleted/Meta gating to host soft-delete support matrix. Companion helper here: `getRevType` (:885–898) — bt↔hm / many_to_one↔one_to_many inversion with NO mm/oo case (falls through returning input).
