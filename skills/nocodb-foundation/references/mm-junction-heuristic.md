<!-- capsule-v2 -->
# mm junction heuristic — what shape test promotes a two-FK table into many-to-many metadata, and how is idempotency guaranteed?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does NocoDB detect that a physical table IS a junction table and synthesize MM columns on both parents without creating duplicates on re-runs?

## mm junction heuristic
**Path/Symbol:** `packages/nocodb/src/helpers/populateMeta.ts` — `isMMRelationExist` (:51–78), `extractAndGenerateManyToManyRelations` (:81–242; shape gate :102–110, existence probe :117–129, insert arms :131–210, system-field marking :214–236).
**Signature:** shape gate: `belongsToCols.length === 2 && normalColumns.length < 5 && assocModel.primaryKeys.length === 2 && primaryKeys.every(pk => belongsToCols.some(c => c.colOptions?.fk_child_column_id === pk.id))`.
**Data Shape:** an inserted MM column carries `fk_mm_model_id` (junction model), `fk_child_column_id`/`fk_parent_column_id` (far-side PK endpoints), plus `fk_mm_child_column_id`/`fk_mm_parent_column_id` (junction-side FK columns).

### Decisive source
```ts
// :102–110 — the four-part shape gate (comment verbatim):
// todo: impl better method to identify m2m relation
if (
  belongsToCols?.length === 2 &&
  normalColumns.length < 5 &&
  assocModel.primaryKeys.length === 2 &&
  // check if both belongsToCol target primary keys
  assocModel.primaryKeys.every((pk) =>
    belongsToCols.some((c) => c.colOptions?.fk_child_column_id === pk.id),
  )
) {
// :65–74 — existence probe matches the mm twin by junction + endpoint ids:
if (
  colOpt &&
  isMMOrMMLike(col) &&
  colOpt.fk_mm_model_id === assocModel.id &&
  colOpt.fk_child_column_id === colChildOpt.fk_child_column_id &&
  colOpt.fk_mm_child_column_id === colChildOpt.fk_child_column_id
)
```

**Flow:** for each candidate junction → verify exactly two belongsTo FKs covering exactly the composite PK and <5 normal columns (a pure bridge, no payload columns) → for BOTH parent models probe existing LTAR columns via `isMMRelationExist` → insert missing MM column per side with inflected plural titles (`pluralize(modelB.title)`), `formatLinkDbMapping` description, and version comment "mm has a junction table (fk_mm_model_id set), so the version heuristic resolves LinkToAnotherRecord to LTAR v2" (:153–155) → `Model.markAsMmTable(context, assocModel.id, true)` → mark each side's HAS_MANY column that shares the same child/parent FK pair as a system field (break after first match).
**Invariant:** Idempotency rests on the three-way probe (`fk_mm_model_id` + `fk_child_column_id` + `fk_mm_child_column_id`) matching by IDs, not titles — re-running must not duplicate MM columns. The else-branch (:237–240) DEMOTES: if a previously-marked mm table no longer passes the shape gate, `markAsMmTable(..., false)` un-marks it. Note the sibling implementation in `services/meta-diffs.service.ts:1353` has the SAME shape gate but adds corrupted-data guards (skip when `colOptions` or related models are missing) and omits the pk-covers-bt check — the two copies have deliberately diverged.
**Probe:** `grep -rc "normalColumns.length < 5" packages/nocodb/src/helpers/populateMeta.ts packages/nocodb/src/services/meta-diffs.service.ts | wc -l` → `2` (one in each copy).
**Coverage caveat:** grep-derived; behavior pinned to source ranges.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "extractAndGenerateManyToManyRelations isMMRelationExist", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-part shape gate, ID-based existence probe, demote-else branch, and the HAS_MANY→system-field marking loop; adapt pluralize/inflection titles; omit apiCount increments. If porting meta-diff sync too, port the service copy's corrupted-data guards alongside — they exist only in the twin.
