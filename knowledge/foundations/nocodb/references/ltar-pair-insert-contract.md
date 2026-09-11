<!-- capsule-v2 -->
# LTAR pair-insert contract — what must a port insert to create ONE link, and which fields encode cross-base and self-reference semantics?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** createHmAndBtColumn inserts two columns for one relation — what per-side context swap, cascade metadata, and system-flag rules are load-bearing?

## LTAR pair-insert contract
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `createHmAndBtColumn` (:44–213), `createOOColumn` (:229–399).
**Signature:** `createHmAndBtColumn(context, req, child: Model, parent: Model, childColumn: Column, childView?, type?, alias?, fkColName?, virtual=false, isSystemCol=false, columnMeta=null, isLinks=false, colExtra?, parentColumn?, isCustom=false, columnWebhookManager?, idHints?: LtarHmBtIds, out?: LtarHmBtIds) → Promise<Column>` (returns the hm/parent side).
**Data Shape:** bt row lives on CHILD model; hm row lives on PARENT model; `LtarHmBtIds {childRelColId, savedColumnId}` supports sandbox-replay id pinning (CE callers leave undefined).

### Decisive source
```ts
// :80–86 + :104 + :109–110 + :115 — cross-base props, hardcoded rules, self-ref:
if (parent.base_id !== child.base_id) {
  crossBaseProps = {
    fk_related_base_id: parent.base_id,
    fk_related_source_id: parent.id,
  };
}
...
dr: 'NO ACTION',
ur: 'NO ACTION',
// if self referencing treat it as system field to hide from ui
system: isSystemCol || parent.id === child.id,
// :119–120:
// Custom links are always V1
...(isCustom ? { version: 1 } : {}),
```

**Flow:** bt arm: unique alias defaults to parent title; Column.insert under `{...context, base_id: child.base_id}` (per-side context!) with `type:'bt'`, uidt LinkToAnotherRecord (Links only when `isLinks` on the hm side), FK endpoints from childColumn + `parentColumn?.id || parent.primaryKey.id`; webhook manager notified per column; AppEvents.COLUMN_CREATE emitted unless system. hm arm mirrors with pluralized child title and `fk_target_view_id: childView?.id`. OO variant adds `RelationTypes.ONE_TO_ONE` + `meta.bt: true` ONLY on the child column (:300–306 comment: "one-to-one relation is combination of both hm and bt to identify table which have foreign column(similar to bt)"), stripped from the parent's meta before insert (:344–347), and skips the isSystemCol gate on app-hooks emission.
**Invariant:** (1) Each insert runs under the OWNING SIDE's base context — using the caller's context for both rows misplaces rows in cross-base relations. (2) `dr`/`ur` are HARDCODED 'NO ACTION' with a comment binding them to `relationCreate` in ColumnsService so `shouldCascadeLinkCleanup` sees truthful metadata (:106–108). (3) Self-referencing links (`parent.id === child.id`) are forced system/hidden regardless of isSystemCol. (4) Cross-base props point OPPOSITE ways per side (bt→parent's base, hm→child's base).
**Probe:** `grep -c "dr: 'NO ACTION'" packages/nocodb/src/helpers/columnHelpers.ts` → `4`; `grep -c "system: isSystemCol || parent.id === child.id" packages/nocodb/src/helpers/columnHelpers.ts` → `2`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "createHmAndBtColumn createOOColumn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-row-per-link shape, per-side contexts, hardcoded NO ACTION pair, self-ref system rule, custom-links-always-v1 stamp, and the oo meta.bt discriminator; adapt webhook/app-hook emission to host event bus.
