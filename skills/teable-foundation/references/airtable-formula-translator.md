<!-- capsule-v2 -->
# Airtable formula translation — how far can a token-level translator go before it must refuse?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What subset of an Airtable formula translates to a teable formula, what is rewritten, and why does the translator return failure instead of best-effort output?

## Lexer + conservative token rewrite
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-formula-translator.ts`:`translateAirtableFormula` (:202–253) + `tokenize` (:139–191).
**Signature:** `translateAirtableFormula(formula: string): IFormulaTranslation` — `{ok:true, expression}` | `{ok:false, reason}`.
**Data Shape:** tokens are `string | field | number | ident | punct | ws`; `{fldXXX}` field spans stay OPAQUE (never tokenized internally); ~90-entry `airtableToTeableFunction` name map (identical names + renames ARRAYJOIN→ARRAY_JOIN, DATEADD→DATE_ADD, ISERROR→IS_ERROR, REGEX_REPLACE→REGEXP_REPLACE).

### Decisive source
```ts
if (upper === 'TRUE' || upper === 'FALSE') {
  out.push(upper);
  if (isCall) {
    // Drop Airtable's empty `()`: TRUE() / FALSE() → TRUE / FALSE.
    const closeParen = nextSignificant(tokens, callParen + 1);
    if (closeParen < 0 || tokens[closeParen].raw !== ')') {
      return { ok: false, reason: `${upper}() called with arguments` };
    }
    k = closeParen;
  }
  continue;
}
...
if (token.raw === '^') {
  return { ok: false, reason: 'unsupported operator "^" (power)' };
}
```

**Flow:** trim/empty check → tokenize (unterminated string or `{field}` ⇒ fail) → single pass over tokens: `^` refuses, TRUE()/FALSE() become literals (argued calls refuse), bare identifiers that aren't followed by `(` refuse, unknown function names refuse; everything else passes through verbatim.
**Invariant:** Refusal is a feature — the importer falls back to a typed static snapshot (`snapshotMappingFromResult`) instead of emitting a broken live formula. Field references stay `{fldXXX}` here and are remapped later by the SAME id-map mechanism every other reference uses. String contents can never be mistaken for functions because strings tokenize opaquely.
**Probe:** `grep -cF "unsupported operator" apps/nestjs-backend/src/features/airtable-import/airtable-formula-translator.ts` returns 1. Direct tests: `airtable-formula-translator.spec.ts` — it('rejects unsupported functions so the importer can fall back to a snapshot') :36, it('rejects the unsupported "^" power operator') :41, it('converts TRUE()/FALSE() calls into boolean literals') :28.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"translateAirtableFormula airtableToTeableFunction tokenize","limit":5,"detail":"ids"}'
```

## Verdict
Adopt translate-or-refuse with opaque field/string spans for any formula-language bridge; adapt the function-name map to host grammar; omit Airtable-specific names. Coverage caveat: none.
