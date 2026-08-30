<!-- capsule-v2 -->
# Airtable derived-field creation — why do lookups/counts/rollups/formulas each get their own late phase and retry grammar?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How are the four derived field kinds created after data, what does each require to go live, and how does the formula loop converge?

## Four creation passes + formula dependency retries
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` — `createLookupFields` (:1243–1301), `createCountFields` (:1304–1359), `createRollupFields` (:1368–1455), `createFormulaFields` (:1464–1523).
**Signature:** each `private async createXFields(plan, tableIdMap, ...): Promise<void>`; formula loop: `while (pending.length > 0)` over `{tablePlan, formulaField}` pairs.
**Data Shape:** lookups need link + target PLAIN field ids; counts compile to rollup `countall({values})` over the foreign PRIMARY field; rollups carry optional record-selection filter mapped through `mapAirtableFilter` with a dropped-conditions counter; formulas remap `{fldXXX}` tokens at create time.

### Decisive source
```ts
let pending = plan.tables.flatMap((tablePlan) =>
  tablePlan.formulaFields.map((formulaField) => ({ tablePlan, formulaField }))
);
while (pending.length > 0) {
  const failed = [];
  for (const { tablePlan, formulaField } of pending) {
    const fieldRo = { ..., type: FieldType.Formula,
      options: { expression: remapReferences(formulaField.expression) } };
    try { await this.fieldOpenApiV2Service.createField(...); }
    catch (error) { failed.push({ tablePlan, formulaField, error }); }
  }
  if (failed.length === pending.length) {
    // No progress this pass: the remaining failures are real, report them.
    for (const {...} of failed) { issues.push({ code: 'fieldSkipped', ... }); }
    break;
  }
  pending = failed.map(({ tablePlan, formulaField }) => ({ tablePlan, formulaField }));
}
```

**Flow:** after records+links → lookups skip (fieldSkipped) when their link OR target wasn't imported; target must have been planned plain → counts degrade to a number snapshot at PLAN time when the link is invalid (`isValid !== false` + imported-link check in the mapper), else live `countall` rollups → rollups map their aggregation + best-effort filter (untranslatable conditions dropped with a count in the degradation reason) → formulas retry in dependency passes until a pass makes no progress, then report every survivor.
**Invariant:** A single uncomputable field is reported, never fatal. The no-progress check compares against THIS pass's size, not a counter — that's what makes the loop terminate on genuinely broken references while still resolving multi-level formula-on-formula chains.
**Probe:** `grep -cF "countall({values})" apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` returns 1; direct test: `airtable-schema-mapper.spec.ts` it('plans count as a rollup and lookup as a real lookup') :259.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"createFormulaFields createRollupFields createLookupFields createCountFields","limit":5,"detail":"ids"}'
```

## Verdict
Adopt per-kind late creation passes with dependency-retry convergence for any staged schema materialization; adapt field-kind specifics; omit teable's exact issue codes if the host has its own ledger. Coverage caveat: none.
