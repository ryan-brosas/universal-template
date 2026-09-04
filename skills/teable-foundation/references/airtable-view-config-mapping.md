<!-- capsule-v2 -->
# Airtable view-config mapping — how do filters/sorts/groups translate without guessing?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does an Airtable filter tree become a teable filter (operators, select-option ids, date modes), and which conditions must be dropped rather than approximated?

## mapAirtableFilter + operator dispatch + per-view-type options
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-view-config-mapper.ts`:`mapAirtableViewConfig` (:373–396), `mapOperator` (:103–142), `mapFilterValue` (:183–198).
**Signature:** `mapAirtableViewConfig(params): IMappedViewConfig` where ctx = `{resolveField(columnId) → IImportFieldMeta|undefined, resolveSelectOptionName(columnId, optionId) → string|undefined}`.
**Data Shape:** `IImportFieldMeta {fieldId, type, cellValueType, isMultipleCellValue}` resolved from the CREATED table's live field rows; drops funnel through one `onDrop(reason)` collector that becomes `viewConfigDegraded` issues.

### Decisive source
```ts
// Fields whose Airtable filter value references specific records/collaborators
// (link, user, ...). Those ids cannot be remapped reliably at view-config time,
// so value-based conditions on them are dropped (empty/not-empty still apply).
const isRecordReferenceField = (meta: IImportFieldMeta) =>
  meta.type === FieldType.Link || meta.type === FieldType.User ||
  meta.type === FieldType.CreatedBy || meta.type === FieldType.LastModifiedBy;
...
const operator = mapOperator(leaf.operator, meta);
if (!operator || !getValidFilterOperators(meta).includes(operator)) {
  onDrop(`operator "${leaf.operator}" is not supported on this field`);
  return undefined;
}
```
Date modes: `thisCalendarWeek → currentWeek`, `thisCalendarMonth → currentMonth`, `thisCalendarYear → currentYear`; values validated against `getValidFilterSubOperators(type, operator)` before use.

**Flow:** leaves resolve their field meta (unimported field ⇒ drop with reason) → operator maps by cellValueType/multi-valuedness (`=` ⇒ is/isExactly/isNot..., `isAnyOf`/`|` ⇒ hasAnyOf only when multi, `&` ⇒ hasAllOf multi / isAnyOf scalar) then must survive the host's OWN validity gate (`getValidFilterOperators`) → values convert per family: selects map option IDs→NAMES (cells/filters are name-keyed after import), dates map mode objects with UTC pinning, record-reference fields keep only isEmpty/isNotEmpty → nested groups rebuild recursively, empty groups vanish → sorts/groups remap order enums; kanban takes its stack field from groupLevels[0] (NOT a row grouping), grid maps row heights with legacy `xlarge` alias, unknown row height degrades.
**Invariant:** Anything not faithfully convertible is DROPPED AND REPORTED, never guessed — "the core import is unaffected". Operator validity is re-checked against the target's own rules even when the Airtable operator has a name mapping.
**Probe:** `grep -cF "getValidFilterSubOperators" apps/nestjs-backend/src/features/airtable-import/airtable-view-config-mapper.ts` returns 2; `grep -cF "isRecordReferenceField" ...` returns 2. Direct tests: `airtable-view-config-mapper.spec.ts` it('drops conditions that cannot be converted and reports them, never guessing') :90, it('reads the kanban stack from the group level (a collaborator field, not a guess)') :131.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"mapAirtableViewConfig mapOperator mapFilterLeaf kanbanOptions","limit":5,"detail":"ids"}'
```

## Verdict
Adopt drop-and-report filter translation with host-side validity re-checks for any view-config port; adapt operator vocabularies; omit Airtable metadata key paths. Coverage caveat: none.
