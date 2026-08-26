<!-- capsule-v2 -->
# Airtable field mapping ladder — how does every Airtable type land in a legal teable field, and when does a computed field go live vs snapshot?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What is the per-type mapping table (including the converter vocabulary), and what is the translate-or-snapshot decision tree for formula/rollup/lookup/count fields?

## mapField + snapshotMappingFromResult + primary-field gate
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-schema-mapper.ts`:`mapField` (:402–551), `snapshotMappingFromResult` (:351–399), `applyPrimaryField` (:943–1000).
**Signature:** `mapField(field: IAirtableField, fieldNameById: Map<string,string>): IFieldMapping` — `{kind:'direct', type, options?, converter, degradedTo?}` | `{kind:'skip', reason}`.
**Data Shape:** `IAirtableCellConverter` = 15 string-literal kinds (`string|number|boolean|dateTime|stringArray|user|attachment|barcode|button|aiText|collaboratorText|snapshotText|snapshotNumber|snapshotDate|snapshotCheckbox`) decoupling target type from cell conversion.

### Decisive source
```ts
case 'duration':
case 'autoNumber':
  // Teable has no duration type (Airtable stores duration as seconds) and
  // cannot back-fill auto numbers — keep both as plain numbers.
  return { ...numberMapping(NumberFormattingType.Decimal, { precision: 0 }), degradedTo: 'number' };
...
default:
  // Unknown / future Airtable field types degrade to a text snapshot so
  // the import never fails on them.
  return { kind:'direct', type: FieldType.LongText, options:{}, converter:'snapshotText',
           degradedTo: longTextSnapshotLabel };
```
```ts
const translation = field.type === 'formula' && field.options?.formula && field.options?.isValid !== false
  ? translateAirtableFormula(field.options.formula) : null;
if (translation?.ok) { plan.formulaFields.push({...}); continue; }
if (field.type === 'rollup') {
  const source = rollupSources?.get(field.id);
  const expression = source ? mapAirtableRollupAggregation(source.aggregation) : null;
  ...
}
// else → typed static snapshot via snapshotMappingFromResult(field.options?.result)
```

**Flow:** plain types map directly (email/url/phone → SingleLineText display variants; multiline/richText → LongText; created/modified time → date SNAPSHOT because teable would recompute them to import time; barcode/button → text snapshots) → computed fields try LIVE first (formula translation ok / rollup with shared-model aggregation + imported link), else typed snapshot keyed on the Airtable `result` config → unknown types degrade to LongText snapshots → `applyPrimaryField` forces the first phase-1 field to be primary-compatible (Attachment/Checkbox incompatible ⇒ replaced by text-snapshot primary; link/lookup/count primaries are stripped from their phase lists).
**Invariant:** Every field id enters `fieldIdMap` even when degraded (lookups/formulas referencing it must remap). Degradation always emits a `fieldDegraded` issue with from/to types — never silent. Select choices merge after trim (Airtable allows duplicate names, teable doesn't) and blank names become `(blank N)` — cells reference names only so duplicates cannot be disambiguated anyway.
**Probe:** `grep -cF "(blank \${index + 1})" apps/nestjs-backend/src/features/airtable-import/airtable-schema-mapper.ts` returns 1; `grep -cF "inverseOwns" ...` returns 2. Direct tests: `airtable-schema-mapper.spec.ts` it('falls back to a text snapshot for unknown future field types') :472, it('degrades the primary field to a text snapshot when it maps to an incompatible type') :379, it('snapshots an invalid formula instead of emitting a broken live formula') :297.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildAirtableImportPlan applyPrimaryField snapshotMappingFromResult","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the converter-vocabulary decoupling, live-first/snapshot-fallback computed policy, and never-fail unknown-type degradation; adapt type enums/options shapes; omit Airtable's specific option keys. Coverage caveat: none.
