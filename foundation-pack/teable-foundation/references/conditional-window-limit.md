<!-- capsule-v2 -->
# conditional-window-limit — How is "top-N per group" implemented for a conditional lookup without correlated subqueries?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does `limit` on a conditional lookup interact with the equality join plan?

## ROW_NUMBER() OVER (PARTITION BY keys ORDER BY sort) filtered to rank <= limit
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:generateConditionalLookupFieldCteForScope` (:1616-1939, window plan :1832-1875).
**Signature:** window clause built from `equalityPlan.joinKeys` + optional orderByClause; rank alias `"__cl_rank"`; target pre-projected as `` __cl_target_<fieldId> ``.
**Data Shape:** three stacked subqueries: ranked source (filter+window) → limited source (`WHERE "__cl_rank" <= ?` binding) → aggregate source grouped by the SAME key expressions selecting casted aggregate as reference_value; CTE exposes `conditional_lookup_<id>` (+ twin `conditional_rollup_<id>` column when field.type === ConditionalRollup).

### Decisive source
```ts
const partitionClause = equalityPlan.joinKeys.map((cond) => cond.foreignExpr).join(', ');
const windowOrder = orderByClause ? ` ORDER BY ${orderByClause}` : '';
const windowClause = partitionClause
  ? `PARTITION BY ${partitionClause}${windowOrder}`
  : windowOrder.trim();
const rowNumberExpr = windowClause
  ? `ROW_NUMBER() OVER (${windowClause})`
  : 'ROW_NUMBER() OVER ()';
...
.whereRaw('"__cl_rank" <= ?', [resolvedLimit]);
```

**Flow:** base subquery projects the coerced target expression under a stable alias → equality plan present ⇒ rank rows per host-key group in requested order → cut at normalized limit → aggregate survivors per group. No plan ⇒ plain ordered+limited source aggregated scalar-wise.
**Invariant:** the LIMIT is applied AFTER ranking but BEFORE aggregation, so aggregates see exactly the top-N slice; the partition expressions must be byte-identical on both sides (they are reused from the same joinKeys objects). Sort aliases are per-field deterministic (`__cl_sort_<fieldId>_<fieldId>`).
**Probe:** static byte-exact: `grep -n '__cl_rank' field-cte-visitor.ts` → :1843/:1849; `grep -n '__cl_target_' field-cte-visitor.ts` → :1720.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"generateConditionalLookupFieldCteForScope","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the rank→cut→aggregate stack for per-group top-N. Adapt alias prefixes. Omit the dual rollup/lookup column trick if your CTEs serve one consumer.
