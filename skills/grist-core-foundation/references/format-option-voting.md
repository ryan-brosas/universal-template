<!-- capsule-v2 -->
# Format-option voting — how are display options (currency/percent/decimals/sign-style) inferred from the data itself?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** When a column becomes Numeric, which NumberFormatOptions does the data justify, and how are ties/absences resolved?

## guessOptions() counts modes over distinct values and derives decimals from trailing zeros
**Path/Symbol:** `app/common/NumberParse.ts`: `guessOptions` (:225–328), parens latch (:261–268), mode tally (:273–281), decimals scan (:283–291), mode-majority gate (:294–309), currency-default suppression (:315–319), maxDecimals escalation (:321–325).
**Signature:** `guessOptions(values: (string|null)[]): NumberFormatOptions`.
**Data Shape:** Returns `{numMode?, numSign?: "parens", decimals?, maxDecimals?}` — all optional; `{}` means "guess nothing".

### Decisive source
```ts
if (result < 0 && !isParenthesised) {
  // If we see a negative number not surrounded by parens, assume that any other parens mean something else
  parens = false;
} else if (parens === null && isParenthesised) {
  parens = true;
}
...
const maxCount = Math.max(...Object.values(modes));
if (maxCount === 0) return {};                       // nothing parsed → guess nothing
const maxMode = NumMode.values.find(k => modes[k] === maxCount)!;
if (maxMode !== "decimal" || anyHasDigitGroupSeparator) result.numMode = maxMode;
...
// Specify minimum decimals if trailing 0s were seen. Otherwise explicitly set 0
// to suppress the currency default ($1.00).
if (decimals > 0 || maxMode === "currency" && maxDecimals < this.defaultNumDecimalsCurrency) {
  result.decimals = decimals;
}
const tmpNF = buildNumberFormat(result, {...}).resolvedOptions();
if (maxDecimals > (tmpNF.maximumFractionDigits ?? 0)) result.maxDecimals = maxDecimals;
```

**Flow:** iterate DISTINCT values (`getDistinctValues`) → per value parse with the normalization pipeline → latch parens decision (a single plain negative permanently vetoes paren style) → count modes (decimal/currency/percent/scientific) → majority mode wins but plain decimal is only asserted if SOME value showed a digit group separator → trailing-zero scan sets minimum `decimals`; currency columns with fewer decimals than the locale default get explicit `decimals` so `$1.00` isn't forced on `1`.
**Invariant:** Voting runs over distinct values only (duplicates don't stuff the ballot). `decimals` counts toward a MAX only when a trailing zero proves intent (`1.50` ⇒ ≥2); `1.5` alone never raises it. The final `buildNumberFormat().resolvedOptions()` round-trip checks whether the guessed options would clamp precision — that's when `maxDecimals` gets set explicitly.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "getDistinctValues(values)" app/common/NumberParse.ts && grep -n "anyHasDigitGroupSeparator" app/common/NumberParse.ts | head -3'` → :247 and :232/:271/:307.
Direct tests: `test/common/NumberParse.ts` — guess-options assertions inside the locale matrix; `test/common/ValueGuesser.ts` "should handle formatted numbers" (:68).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"NumberParse guessOptions numMode decimals numSign","limit":5,"detail":"ids"}'
```

## Verdict
Adopt distinct-value voting + trailing-zero decimals + the negative-vetoes-parens latch; adapt the option vocabulary to your formatter; omit the currency-default suppression only if your host has no per-currency fraction default to suppress.
