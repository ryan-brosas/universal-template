<!-- capsule-v2 -->
# Result-shape conversion matrix — bigint/date/string normalization and percent defaultToZero

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do raw driver values become the API's `total.value` union, per statistic function?

## formatConvertValue + convertValueToNumberOrString
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` — `formatConvertValue` (:207–230), `convertValueToNumberOrString` (:232–240); result-key matching loop :166–189.
**Signature:** `formatConvertValue(currentValue: unknown, aggFunc?: StatisticsFunc): number | string | null`.
**Data Shape:** API value = number | string | null (dates serialize as ISO strings).

### Decisive source
```ts
private convertValueToNumberOrString(currentValue: unknown): number | string | null {
  if (typeof currentValue === 'bigint' || typeof currentValue === 'number') {
    return Number(currentValue);
  }
  if (isDate(currentValue)) {
    return currentValue.toISOString();
  }
  return currentValue?.toString() ?? null;
}
...
if (defaultToZero.includes(aggFunc)) {   // Percent* family
  convertValue = convertValue ?? 0;
}
```

**Flow:** Driver rows are keyed by alias (`item.alias === key || item.fieldId === key`) so multiple funcs of one field stay distinct; each value passes the converter: bigint/number → Number (pg COUNT/SUM arrive as bigint), Date → ISO string (Earliest/LatestDate), everything else → string or NULL (the months-range payload). Percent-family NULLs then coerce to 0 client-side.
**Invariant:** The `?? null` tail means an UNDEFINED aggregate (empty scope on Min/Max) surfaces as explicit null — the client distinguishes "no rows" from 0 EXCEPT for percentages where product decision says empty table = 0%. Keying by `alias ?? fieldId` matters because legacy callers pass bare fieldIds while view-driven stats always alias `${fieldId}_${func}`; matching BOTH keeps wire compat across the two entry paths. Porters who JSON-serialize before conversion lose Date instances and emit raw pg bigint strings.
**Probe:** `grep -cF 'defaultToZero' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 2; `grep -cF 'convertValueToStringify' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "formatConvertValue convertValueToNumberOrString aggregation", limit: 10 });
```

## Verdict
Adopt a single result-normalization point per read surface; adapt the type ladder to your driver's return types; document which functions get empty→zero coercion.
