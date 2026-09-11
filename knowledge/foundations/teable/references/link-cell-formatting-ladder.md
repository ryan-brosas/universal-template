<!-- capsule-v2 -->
# link-cell-formatting-ladder — How does a link cell's display title get formatted (choice/number/date/user) inside CTE selection?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which visitor turns a foreign primary-field expression into its user-facing text form for `{id,title}` objects?

## FieldFormattingVisitor: field.accept over a wrapped expression, dialect-backed per type
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-formatting-visitor.ts` (whole 246L); primary consumer `field-cte-visitor.ts:visitLinkField` (:581) + conditional-rollup formatting (:1370-1373).
**Signature:** `new FieldFormattingVisitor(fieldExpression: string, dialect: IRecordQueryDialectProvider)`; `field.accept(visitor): string`.
**Data Shape:** input = raw SQL expression referencing the target column; output = SQL producing display text; helpers route through the DIALECT (`toText`, `formatNumber`, `formatNumberArray`, `formatDate`, `formatDateArray`) so all PG specifics stay in one class.

### Decisive source
```ts
private applyNumberFormatting(formatting: INumberFormatting): string {
  return this.dialect.formatNumber(this.fieldExpression, formatting);
}
// array variants format PER ELEMENT then string_agg:
private formatMultipleNumberValues(formatting: INumberFormatting): string {
  return this.dialect.formatNumberArray(this.fieldExpression, formatting);
}
```
Dialect side (pg): decimal → `ROUND(CAST(x AS NUMERIC), p)::TEXT`; percent → `ROUND(CAST(x*100 AS NUMERIC), p)::TEXT || '%'`; currency → symbol-prefix; arrays → `string_agg(formatted, ', ' ORDER BY ord) FROM jsonb_array_elements(...) WITH ORDINALITY`.

**Flow:** visitLinkField takes the physical primary-field expression → wraps in FieldFormattingVisitor → target field's accept() picks the type arm (select choices render names, numbers apply formatting incl. currency/percent, dates apply field timezone/patterns, users resolve snapshot titles) → self-join contexts rewrite the default alias to the override via replaceAll → result becomes the `title` slot of buildLinkJsonObject.
**Invariant:** formatting is applied at READ time from field OPTIONS — changing a number field's currency later changes historical cells' display (unlike user snapshots). Array formatters must preserve element order via WITH ORDINALITY.
**Probe:** upstream direct spec pins two formatter arms (`pg-record-query-dialect.spec.ts`: formatStringArray NULL fast-paths + snapshot fallback :31-70); static byte-exact: `grep -n 'class FieldFormattingVisitor' field-formatting-visitor.ts` → :33.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"FieldFormattingVisitor","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the visitor+dialect split so formatting stays driver-contained. Adapt format vocabularies. Omit nothing.
