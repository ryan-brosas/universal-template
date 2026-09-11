<!-- capsule-v2 -->
# Locale-number normalization pipeline — what exact rewrite order turns "€ 1.234,56–" into a JS-parseable number?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** In what order are currency/percent/parens/digits/separators normalized so no step corrupts another?

## parse() runs nine ordered rewrites, each reporting its detection into ParsedOptions
**Path/Symbol:** `app/common/NumberParse.ts`: `parse` (:145–223), `removeSymbol` helper (:336–340), double minus replacement (:191–192), trailing-minus move (:195–197), parenthesised-negative rule (:207–212).
**Signature:** `parse(value): { result: number, cleaned: string, options: ParsedOptions } | null`.
**Data Shape:** `ParsedOptions = { isPercent, isCurrency, isParenthesised, hasDigitGroupSeparator, isScientific }` — consumed by guessOptions voting.

### Decisive source
```ts
const [value2, isCurrency] = removeSymbol(value, this.currencySymbol);
const [value3, isPercent]   = removeSymbol(value2, this.percentageSymbol);
value = value3.replace(NumberParse.removeCharsRegex, "");   // AFTER currency: some currencies contain spaces
const isParenthesised = value.startsWith("(") && value.endsWith(")");
if (value === "") return null;                              // Number('') === 0 :facepalm:
value = value.replace(this._exponentSeparatorRegex, "e");   // BEFORE digit replacement (may contain locale digits)
value = this._replaceDigits(value);                         // \d doesn't work for locale digits until now
value = value.replace(this._digitGroupSeparatorRegex, "$1");// requires ≥2 following digits (India pairing)
value = value.replace(this.decimalSeparator, ".");          // AFTER group-separator removal ('.' may BE that separator)
value = value.replace(this.minusSign, "-");                 // TWICE: scientific notation can hold two minus signs
let result = Number(value);
if (isNaN(result)) return null;
if (isParenthesised) { if (result <= 0) return null; result = -result; }
if (isPercent) result *= 0.01;
```

**Flow:** strip currency → strip percent → strip invisible marks → paren-detect → exponent normalize → digit transliterate → drop group separators → decimal normalize → minus normalize (×2) → `Number()` (stricter than parseFloat: no trailing junk). `(123)` means −123 but `(-123)` is an ERROR (result ≤ 0 rejected).
**Invariant:** ORDER IS THE CONTRACT. Currency before whitespace (symbols contain spaces); digits before group-separator removal (`\d` in the regex only matches after transliteration); group removal before decimal replacement (the decimal separator may equal the group separator in some locales); empty-string guard before any `Number()` because `Number('')` is 0. Percent divides by 100 AFTER sign handling. Any reorder silently misparses whole locales.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "value = value.replace(this.minusSign, \"-\")" app/common/NumberParse.ts && grep -cF "result *= 0.01;" app/common/NumberParse.ts'` → :191 AND :192 (two replacements) plus exactly one percent division.
Direct tests: `test/common/NumberParse.ts` locale matrix (:279+) exercises every branch incl. trailing-minus and parenthesised negatives.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"NumberParse parse removeSymbol isParenthesised decimalSeparator","limit":5,"detail":"ids"}'
```

## Verdict
Adopt step order + the `Number('')`-is-0 guard + the `(-123)`-is-error asymmetry verbatim; adapt symbol sources via your host's CLDR; omit the `cleaned`/options side-channel only if nothing votes on formats downstream.
