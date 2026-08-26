<!-- capsule-v2 -->
# truthiness-if-type-matrix — How does IF()/SWITCH() pick a common result type across boolean, numeric, text, and datetime branches?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What ladder turns `IF(cond, "jsonField", 0)` into valid typed SQL?

## Truthiness-score the condition; branch-type resolution: datetime → numeric-with-blank → target-numeric → text/blank
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/select-query/postgres/select-query.postgres.ts:if` (:1615-1668) + `truthinessScore` (:1559-1602).
**Signature:** `if(condition, valueIfTrue, valueIfFalse): string`.
**Data Shape:** condition always compiles to `CASE WHEN COALESCE(score) = 1 …` where score ∈ {0,1} via boolean cast / json emptiness / trusted-numeric compare / pg_typeof dispatch.

### Decisive source
```ts
const resultIsDatetime = targetType === DbFieldType.DateTime || this.isDateLikeOperand(1) || this.isDateLikeOperand(2);
if (resultIsDatetime) { /* both branches tzWrap'd; blanks become NULL */ }
const numericWithBlank = (trueIsBlank && !falseIsHardText && !falseIsText)
                      || (falseIsBlank && !trueIsHardText && !trueIsText);
...
const targetIsNumeric = targetType === Real || Integer;
if (targetIsNumeric || (hasNumericBranch && !hasTextBranch)) { /* toNumericSafe both */ }
```
truthinessScore dispatch: real boolean column → bare wrapped expr (readable/stable for tests); boolean-ish text → `::boolean`; json/multi → text-in('null','[]','{}','') probe; trusted numeric → <>0; else pg_typeof-driven three-way CASE.

**Flow:** score condition → classify branches (blank/hard-text/text/numeric/datetime + context targetDbFieldType) → first matching rung wins: datetime pair → numeric-with-blank → declared/target numeric → text coercion with blank→NULL normalization.
**Invariant:** blank literals degrade to NULL inside typed branches so the CASE keeps one column type; the pg_typeof fallback exists precisely because formula params can arrive without metadata. Upstream spec pins two rungs byte-level: boolean cast before COALESCE (`((('true')::text)::boolean`) and json-numeric IF (`to_jsonb("__json_numeric")`).
**Probe:** upstream direct spec `select-query.postgres.spec.ts:48-90` (truthinessScore describe block); static byte-exact: `grep -n 'resultIsDatetime' select-query.postgres.ts` → :1617/:1619; `grep -n 'pg_typeof\${wrapped}' select-query.postgres.ts` → :1592.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"truthinessScore","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the rung order exactly. Adapt type enum. Omit nothing — each rung exists because a PG type error occurred without it.
