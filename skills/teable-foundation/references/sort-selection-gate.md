<!-- capsule-v2 -->
# sort-selection-gate — Why does sorting silently ignore fields that are not in the selection while filtering does not?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the sort-side counterpart of filter augmentation, and why the asymmetry?

## Sort compiles only over selectionMap keys
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:buildSort` (:753-773, gate at :760-768).
**Signature:** `private buildSort(qb, table, sort: ISortItem[], selectionMap: IReadonlyRecordSelectionMap)`.
**Data Shape:** `allowedIds = new Set(selectionMap.keys())`; field map built ONLY from allowed ids (id and name keyed); non-selected sort items drop out of the compiled ORDER BY rather than erroring.

### Decisive source
```ts
// Restrict sortable fields to those present in the current selection (permission-respected)
const allowedIds = new Set<string>(Array.from(selectionMap.keys()));
const map = table.fieldList.reduce((acc, field) => {
  if (!allowedIds.has(field.id)) return acc;
  acc[field.id] = field;
  acc[field.name] = field;
  return acc;
}, {} as Record<string, FieldCore>);
this.dbProvider.sortQuery(qb, map, sort, undefined, { selectionMap }).appendSortBuilder();
```

**Flow:** selectionMap reflects the projection the visitor actually emitted (permission-respecting) → buildSort intersects requested sorts with it → dbProvider emits ORDER BY for surviving items only.
**Invariant:** the comment names the intent: sorting is a channel where a hidden field could leak values via ordering side channels; filtering is a predicate over data the query already reads. Filter AUGMENTS its map (:716 buildFilter); sort RESTRICTS to it. A porter who "fixes" either asymmetry changes the security posture.
**Probe:** static byte-exact: `grep -n 'allowedIds.has(field.id)' ...service.ts` → :763; contrast probe `grep -n 'augmentedSelection.set' ...service.ts` → :738.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildSort","limit":5,"detail":"ids"}'
```

## Verdict
Adopt both halves of the pair together. Adapt naming. Omit nothing — the documented permission rationale is the porting contract.
