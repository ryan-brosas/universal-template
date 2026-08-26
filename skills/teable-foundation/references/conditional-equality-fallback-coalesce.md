<!-- capsule-v2 -->
# conditional-equality-fallback-coalesce — What value does a host row with NO matching foreign rows get from an equality-plan conditional rollup?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are count/sum/average vs max/min NULL results handled after the LEFT JOIN to counts?

## getConditionalEqualityFallback: numeric fns → 0::double precision; max/min → typed NULL; others → raw reference_value
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:getConditionalEqualityFallback` (:1136-1153) + COALESCE application (:1509-1515).
**Signature:** `private getConditionalEqualityFallback(aggregationFn: string, field: FieldCore): string | null`.
**Data Shape:** `COALESCE(counts."reference_value", fallback)` emitted as `conditional_rollup_<id>`; null fallback passes the value through untouched (NULL stays NULL for max/min).

### Decisive source
```ts
switch (aggregationFn) {
  case 'countall': case 'count': case 'counta':
  case 'sum': case 'average':
    return '0::double precision';
  case 'max': case 'min': {
    const dbType = field.dbFieldType ?? DbFieldType.Text;
    return this.dialect.typedNullFor(dbType);
  }
  default:
    return null;
}
```

**Flow:** equality plan joins every host row to its per-key counts row → hosts with zero matching foreign rows get a NULL reference_value from the join → COALESCE substitutes the fn-appropriate default so the rollup cell matches what a correlated aggregate would have produced (COUNT()=0, SUM()=0, MAX=NULL).
**Invariant:** the defaults mirror SQL aggregate semantics over the empty set — copying the `0` to max/min (a "simplification" a porter might make) silently turns empty-set MAX into 0 and corrupts comparisons. Non-listed fns (array_join etc.) never reach this path because they're excluded from the equality-enabled set.
**Probe:** static byte-exact: `grep -n "'0::double precision'" field-cte-visitor.ts` → :1142.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"getConditionalEqualityFallback","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the semantic-preserving default table. Adapt cast text. Omit nothing.
