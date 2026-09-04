<!-- capsule-v2 -->
# loose-numeric-coercion — What is the never-throw SQL recipe for casting arbitrary text/json to a number?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is `Value("abc")` compiled so Postgres never raises?

## REGEXP_REPLACE strip → NULLIF → COLLATE "C" anchored match → cast, ELSE NULL
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/select-query/postgres/select-query.postgres.ts:looseNumericCoercion` (:153-186) + json variant `numericFromJson` (:187-198) + array sum/count pair `buildNumericArrayAggregation` (:199-210).
**Signature:** `private looseNumericCoercion(expr: string, opts?: { collate?: boolean; guardDateLike?: boolean }): string`.
**Data Shape:** output always a CASE yielding `double precision | NULL`; date-like inputs (`2024/12/03`) can be nulled via opt-in guard; deterministic `COLLATE "C"` on every comparison.

### Decisive source
```sql
REGEXP_REPLACE((expr)::text COLLATE "C", '[^0-9.+-]', '', 'g')  ->  cleaned = NULLIF(..., '')
CASE
  WHEN cleaned IS NULL THEN NULL
  WHEN cleaned COLLATE "C" ~ '^[+-]{0,1}(\d+(\.\d+){0,1}|\.\d+)$' COLLATE "C"
    THEN cleaned::double precision
  ELSE NULL
END
```
JSON variant branches first on `jsonb_typeof(to_jsonb(expr)) = 'array'` and SUMs the per-element numeric CASE over `jsonb_array_elements_text`.

**Flow:** literal fast path (`isNumericLiteral`, incl. wrapped casts like ((7)::double precision)) → text coercion with strip+match → json/array variant sums only elements matching the SAME anchored pattern.
**Invariant:** three load-bearing details a porter drops at their peril — (1) the regex deliberately contains NO '?' because these strings transit knex.raw (see question-mark-literal-split); (2) all regex comparisons pin `COLLATE "C"` so locale rules can't reject digits; (3) failure returns NULL, which callers COALESCE to 0 (`collapseNumeric`) — the function NEVER throws.
**Probe:** static byte-exact counts at pin: `grep -c 'COLLATE "C"' select-query.postgres.ts` → 10; `grep -c 'jsonb_array_elements_text' select-query.postgres.ts` → 8; upstream spec pins IF-side behavior in `select-query.postgres.spec.ts`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"looseNumericCoercion","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the recipe verbatim for PG targets. Adapt type name (double precision vs NUMERIC). Omit the driver fallbacks for non-PG.
