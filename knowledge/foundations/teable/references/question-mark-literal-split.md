<!-- capsule-v2 -->
# question-mark-literal-split — How are `?` characters inside formula string literals kept out of knex's binding parser?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Why does a literal "yes?" break raw SQL builders, and what is the fix shape?

## Split the literal on '?' and reassemble from a bound-parameter expression
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/sql-conversion.visitor.ts:visitStringLiteral` (:323-354) + `getQuestionMarkExpression` (:298).
**Signature:** `visitStringLiteral(ctx: StringLiteralContext): string`.
**Data Shape:** no-`?` fast path → plain stringLiteral; else segments split on '?' with a parameterized char expression spliced between; zero segments → charExpr alone.

### Decisive source
```ts
if (!unescapedString.includes('?')) {
  return this.formulaQuery.stringLiteral(unescapedString);
}
const charExpr = this.getQuestionMarkExpression();
const parts = unescapedString.split('?');
...
if (segments.length === 0) {
  return charExpr;
}
return this.formulaQuery.concatenate(segments);
```
The same trap is documented on the numeric-coercion side of both db-providers:
```ts
// Avoid "?" in the regex so knex.raw doesn't misinterpret it as a binding placeholder.
```
(select-query.postgres.ts:171, generated-column-query.postgres.ts:164 — numeric regexes are written without '?').

**Flow:** user formula contains `'Yes?'` → naive inlining would make knex treat the ? as bind #1 → visitor splits and rebuilds via CONCAT so every ? arrives as a VALUE not a placeholder.
**Invariant:** any string that transits knex.raw must be ?-free; this capsule plus the regex comment define the two places the invariant is enforced (literals at parse time, patterns at coercion time). Porters adding new SQL templates must keep both.
**Probe:** static byte-exact: `grep -n "includes('?')" sql-conversion.visitor.ts` → :328; cross-check `grep -rn "knex.raw doesn't misinterpret" db-provider/select-query/postgres db-provider/generated-column-query/postgres` → 2 hits (:171/:164).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"getQuestionMarkExpression","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the split-and-concatenate defense for any knex-based builder. Adapt the char expression to your dialect. Omit nothing — this is a whole-family footgun fix.
