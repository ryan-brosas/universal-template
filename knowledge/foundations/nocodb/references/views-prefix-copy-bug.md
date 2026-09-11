<!-- capsule-v2 -->
# populateMeta views-wave prefix bug — what does copying the wrong filter list silently do?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** In the views phase of populateMeta, why is the prefix-filter result assigned back to `views` yet computed from `tables` — and what should a porter preserve or fix?

## populateMeta views-wave prefix bug
**Path/Symbol:** `packages/nocodb/src/helpers/populateMeta.ts` — `views` mapping (:573–584), suspicious reassignment (:586–591), `viewsCount` (:593).
**Signature:** `let views = (await sqlClient.viewList(...))?.data?.list?.map(v => ({order, table_name: v.view_name, title}))`.
**Data Shape:** for meta+prefixed sources the variable is REPLACED by a filtered copy of the TABLES array.

### Decisive source
```ts
// :586–593 — verbatim; note the source array:
/* filter based on prefix */
if (source.is_meta && base?.prefix) {
  views = tables.filter((t) => {
    return t?.tn?.startsWith(base?.prefix);
  });
}

info.viewsCount = views.length;
```

**Flow:** viewList rows are aliased into `{order, table_name, title}` → IF the source is meta-managed AND a base prefix exists, `views` is overwritten with `tables.filter(tn startsWith prefix)` — i.e. TABLE rows replace VIEW rows entirely → `info.viewsCount` then reports the count of prefixed tables, and the subsequent `viewMetasInsert` wave inserts Models for those tables AGAIN (as `ModelTypes.VIEW`, second insert of the same `table_name`) instead of for actual views.
**Invariant:** For the port: this is a latent upstream defect class — a copy-paste from the tables block (:309–314 filters `tables` correctly). A faithful port must decide consciously: either replicate byte-for-byte (bug-compatible with NocoDB behavior for prefixed meta sources) or fix to `views.filter(v => v.view_name?.startsWith(base?.prefix))`. The non-prefixed path (external sources without base prefix — the common case) never enters the branch and behaves correctly.
**Probe:** `grep -c "views = tables.filter" packages/nocodb/src/helpers/populateMeta.ts` → `1`.
**Coverage caveat:** grep-derived; flagged as suspected-defect rather than verified-by-test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "populateMeta viewList viewsCount", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wave structure; treat :587–591 as a recorded defect decision point, NOT an invariant to preserve blindly. Porters must not "clean it up" silently when bug-compatibility matters, nor inherit it when building fresh.
