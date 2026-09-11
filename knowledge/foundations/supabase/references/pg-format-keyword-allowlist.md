<!-- capsule-v2 -->
# keyword() allowlist grammar — how do UI-supplied trigger timing words stay injection-proof?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** How can a dropdown-supplied SQL keyword (trigger timing, generation type) be interpolated without becoming an arbitrary-control-phrase channel?

## Allowlisted keyword gate
**Path/Symbol:** `packages/pg-meta/src/pg-format/index.ts` : `keyword` (:227-237), `ALLOWED_MULTI_WORD_KEYWORDS` (:219).
**Signature:** `export function keyword(value: string): SafeSqlFragment`.
**Data Shape:** input must be a single word matching `/^[A-Za-z][A-Za-z0-9_]*$/` OR an exact case-insensitive member of `{'INSTEAD OF', 'BY DEFAULT'}`. Everything else throws `Error('Not a valid keyword: ...')`.

### Decisive source
```ts
// Multi-word SQL keyword phrases callers are allowed to pass to `keyword()`.
// Compared case-insensitively. Any phrase not listed here must be expressed as
// separate single-word `keyword()` calls composed via `safeSql`, so that
// arbitrary control phrases (e.g. "DROP TABLE") can't slip through.
const ALLOWED_MULTI_WORD_KEYWORDS = new Set(['INSTEAD OF', 'BY DEFAULT'])

export function keyword(value: string): SafeSqlFragment {
  if (/^[A-Za-z][A-Za-z0-9_]*$/.test(value)) {
    return value as SafeSqlFragment
  }
  if (ALLOWED_MULTI_WORD_KEYWORDS.has(value.toUpperCase())) {
    return value as SafeSqlFragment
  }
  throw new Error(`Not a valid keyword: "${value}". Must be a single word matching [A-Za-z][A-Za-z0-9_]*, or one of: ${[...ALLOWED_MULTI_WORD_KEYWORDS].join(', ')}.`)
}
```

**Flow:** single word passes through unchanged · allow-listed phrase passes through with ORIGINAL casing preserved (`'instead of'` stays lowercase in output) · anything else throws — semicolons, quotes, parens, digit-leading tokens, and unknown multi-word phrases are all rejected by the same gate.
**Invariant:** the allowlist is closed under review, not open-ended pattern matching: adding a new multi-word phrase is an explicit source change. The regex deliberately excludes `-`, `'`, `;`, `(`, whitespace — no secondary sanitization exists downstream, so this function IS the boundary.
**Probe:** `packages/pg-meta/test/pg-format.test.ts` describe `'keyword'` — accepts `BEFORE`/`EACH_ROW`/`col2`; case-insensitive `keyword('instead of')` passes; rejects `''`, `'1BEFORE'`, `'BEFORE;'`, `"BE'FORE"`, `'fn()'`, `'DROP TABLE'`, `'DELETE FROM users'`, `'Each Row'` (three-word not on list).
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "pg-format unit test escaping identifier literal E-string backslash doubling", limit: 25 })
// keyword :227-237 rank 8, co-ranked with the whole kernel surface line-exact
```

## Verdict
Adopt the two-gate shape (word regex + closed Set) for any enum-like SQL token fed from UI state; the original-casing-preserved match is what keeps generated SQL readable in diffs. Adapt the Set contents to your grammar's legal phrases only after checking each cannot compose an attack. Omit fuzzy/normalized matching — `toUpperCase()` comparison plus original-casing return is the entire contract.
