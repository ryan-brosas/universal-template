<!-- capsule-v2 -->
# lookup-order-column-tiebreak — What ORDER BY makes repeated multi-value lookups return identical arrays across queries?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the full deterministic sort ladder including the no-order-column fallback?

## order-col NULLS DESC → order ASC → __id ASC; junction vs foreign alias variants; bare record-id fallback
**Path/Symbol:** ladder 1 `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:visitLookupField` (:459-487); ladder 2 (link cells, ts-pattern exhaustive) :604-628.
**Signature:** built from link field config: `usesJunctionTable`, `hasOrderColumn` (`getHasOrderColumn()`), `getOrderColumnName()`.
**Data Shape:** junction arm prefixes `j."__id" ASC`; non-junction uses `"foreignAlias".…`; no order column anywhere → `recordIdRef ASC`.

### Decisive source
```ts
orderByClause = hasOrderColumn
  ? `${JUNCTION_ALIAS}."${order}" IS NULL DESC, ${JUNCTION_ALIAS}."${order}" ASC, ${JUNCTION_ALIAS}."__id" ASC`
  : `${JUNCTION_ALIAS}."__id" ASC`;
...
// ts-pattern exhaustive over {usesJunctionTable, hasOrderColumn} for link cells:
.with({ usesJunctionTable: false, hasOrderColumn: false }, () => `${recordIdRef} ASC`) // Fallback to record ID
.exhaustive();
```

**Flow:** resolve the LOOKUP's owning link field (lookupOptions.linkFieldId) → read its order configuration → emit ladder inside json_agg ORDER BY → rows with NULL order values surface FIRST (IS NULL DESC) so unsorted additions don't hide at the tail.
**Invariant:** exhaustiveness is enforced by ts-pattern — adding a new relationship combination without an ordering arm fails compilation. The __id tiebreak is what makes json_agg output stable when order values tie; dropping it yields nondeterministic cell content that breaks snapshot/undo comparisons.
**Probe:** static byte-exact: `grep -n 'IS NULL DESC' field-cte-visitor.ts` → :479/:483/:612/:620.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"getOrderColumnName","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the four-arm ladder + NULLS-first semantics. Adapt column names. Omit nothing — determinism is the whole point.
