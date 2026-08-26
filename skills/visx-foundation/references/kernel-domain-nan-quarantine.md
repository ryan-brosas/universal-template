<!-- capsule-v2 -->
# Domain derivation with NaN quarantine — how do you build a scale domain from raw data without one bad value killing the chart?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** What happens to null/NaN/invalid-Date values in domain computation, and what does an EMPTY dataset yield?

## flatMap-filter + devWarn + safe defaults
**Path/Symbol:** `packages/visx-kernel/src/domain/useDomain.ts:useDomain` (:67–115); coercers `getNumber`/`getTime` (:36–53); manual `extent` (:55–65).
**Signature:** `useDomain({accessor, data, type: 'linear'|'time'|'band'}) => LinearDomain | TimeDomain | BandDomain`.
**Data Shape:** band → dedup'd string[] via Set (insertion order = category order); linear/time → `[min,max]` tuple; empty → `[0,0]` or `[epoch, epoch]` — NEVER throws.

### Decisive source
```ts
let invalidValues = 0;
const values = stableData.flatMap((datum, index) => {
  const number = type === 'time' ? getTime(value) : getNumber(value);
  if (number === undefined) {
    if (value != null) invalidValues += 1;   // nulls are EXPECTED, not warned
    return [];                               // quarantined
  }
  return [number];
});
if (values.length === 0) {
  warnEmptyData(stableData.length);
  return type === 'time' ? [new Date(0), new Date(0)] : [0, 0];
}
```

**Flow:** structural-memo inputs → per-type extraction (time path accepts Date|string|number via `new Date(v).getTime()`) → finite filter with counter → extent scan → wrap time back into Date objects → memo output. Warnings fire once per unique payload (`devWarn` dedup set).
**Invariant:** invalid values are DROPPED not fatal; null vs non-finite are distinguished (null silent, non-null-invalid counted+warned). The `[0,0]` default keeps downstream scales valid (zero-height domain) instead of NaN-poisoning every rendered shape.
**Probe:** `packages/visx-kernel/test/useDomain.test.tsx` (empty-data + NaN-quarantine cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useStructuralMemo domain", limit: 10, fields: ["signature", "name", "file"] });
// or symbol-exact:
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "warnNaNInData getNumber", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt coercion ladder + quarantine semantics verbatim; adapt DomainType union to your chart kinds; omit the generic typing gymnastics if unneeded.
