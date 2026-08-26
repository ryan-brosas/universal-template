<!-- capsule-v2 -->
# fromnow-tonow-direction-contract — Why does TONOW subtract date-from-now while FROMNOW subtracts now-from-date?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which operand order keeps past dates positive in both functions?

## FROMNOW: now - tzWrapped(date); TONOW: NOW() - date (past-positive), pinned by spec
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/generated-column-query/postgres/generated-column-query.postgres.ts:fromNow`/`toNow` (via buildNowDiffByUnit twin `select-query.postgres.ts:1383-1416`; gencol spec :100-115).
**Signature:** `buildNowDiffByUnit(nowExpr, dateExpr, unit)` — callers choose operand order.
**Data Shape:** unit ladder ms×1000 / s / 60 / 3600 / week 86400·7 / month via AGE months / quarter /3.0 / year AGE years / day 86400.

### Decisive source
```ts
// fromNow:
return this.buildNowDiffByUnit('NOW()', this.tzWrap(date, 0), unit);   // or AT TIME ZONE variant
// toNow (spec-pinned direction):
expect(sql).toContain('NOW() -');
expect(sql).not.toContain(' - NOW()');
```
Upstream direct spec (`generated-column-query.postgres.spec.ts:88-115`): `/ 86400` for day, `/ 3600` for hour, neither for second; TONOW direction assertions above.

**Flow:** resolve tz context (session tz wraps the date operand) → pick now-expression → shared unit scaler emits division ladder.
**Invariant:** the two functions are NOT symmetric aliases — flipping operands flips sign for future/past dates. The spec pins direction byte-level because a refactor once inverted it. Month/year use AGE() rather than epoch division so calendar months stay exact.
**Probe:** upstream direct spec `generated-column-query.postgres.spec.ts` ("applies unit conversion for FROMNOW", "keeps TONOW direction as now minus date"); static byte-exact: `grep -n 'buildNowDiffByUnit(`(NOW()' select-query.postgres.ts` → :1414.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"fromNow toNow","limit":5,"detail":"ids"}'
```

## Verdict
Adopt operand orders + unit ladder as pinned. Adapt tz source. Omit nothing.
