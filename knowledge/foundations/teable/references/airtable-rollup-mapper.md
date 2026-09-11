<!-- capsule-v2 -->
# Airtable rollup mapper — when is a rollup live and when must it snapshot?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What aggregation grammar maps 1:1 onto a teable rollup, and why does anything outside it return null?

## singleAggregation grammar
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-rollup-mapper.ts`:`mapAirtableRollupAggregation` (:38–43).
**Signature:** `mapAirtableRollupAggregation(formulaTextParsed: string): string | null`.
**Data Shape:** input is the shared base model's `formulaTextParsed` (e.g. `"SUM(values)"`); output a teable expression like `sum({values})` or null. 14-entry uppercase→lowercase table (SUM/AVERAGE/MAX/MIN/COUNT/COUNTA/COUNTALL/AND/OR/XOR/ARRAYJOIN/ARRAYUNIQUE/ARRAYCOMPACT/CONCATENATE).

### Decisive source
```ts
// One `FUNC(values)` call and nothing else. ARRAYJOIN also accepts a trailing
// separator argument, which is dropped: Teable's array_join joins with a comma.
const singleAggregation = /^([a-z]+)\s*\(\s*values\s*(?:,[^)]*)?\)$/i;

export const mapAirtableRollupAggregation = (formulaTextParsed: string): string | null => {
  const match = formulaTextParsed.trim().match(singleAggregation);
  if (!match) return null;
  const teableFn = airtableRollupToTeable[match[1].toUpperCase()];
  return teableFn ? `${teableFn}({values})` : null;
};
```

**Flow:** trim → match the single-call grammar → look up the function → emit lowercase teable form over `{values}`; compound/custom aggregations (`SUM(values) * 2`, `ROUND(AVERAGE(values),1)`) and unknown functions return null so the importer falls back to a static typed snapshot instead of a wrong live rollup.
**Invariant:** null is the honest "cannot be live" signal — never a best-effort guess. ARRAYJOIN's separator argument is deliberately dropped with the comma-join behavior documented.
**Probe:** Direct tests: `airtable-rollup-mapper.spec.ts` it('maps every Airtable rollup function to its Teable counterpart') :4, it('returns null for compound or custom aggregations so the importer snapshots them') :34.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"mapAirtableRollupAggregation airtableRollupToTeable singleAggregation","limit":5,"detail":"ids"}'
```

## Verdict
Adopt strict-grammar-or-null mapping for any aggregation-language bridge; adapt the function table; omit Airtable's formulaTextParsed provenance if the host reads aggregations elsewhere. Coverage caveat: none.
