<!-- capsule-v2 -->
# Ninety-percent parse budget — how lossy may bulk type conversion be before the guess is abandoned?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What exact tolerance lets a mostly-numeric column convert while a noisy one stays text?

## guess(): ≤10% of NON-EMPTY values may fail to parse, and every success must round-trip
**Path/Symbol:** `app/common/ValueGuesser.ts`: `abstract class ValueGuesser<T>` `guess` (:52–80), budget line (:58), give-up condition (:73–75), `allowBlank` (:85–87) overridden false ONLY by BoolGuesser (:112–114), NumericGuesser's whitespace-insensitive `isEqualFormatted` (:136–142).
**Signature:** `guess(values: (string|null)[], docSettings: DocumentSettings): GuessResult | null`.
**Data Shape:** Input mixes strings and nulls. Output `{values, colInfo}` or null (= try next type in the ladder).

### Decisive source
```ts
const maxUnparsed = countIf(values, v => Boolean(v)) * 0.1;
let unparsed = 0;
for (const value of values) {
  if (!value) {
    if (this.allowBlank()) { result.push(null); continue; }
    else { return null; }
  }
  const parsed = this.parse(value);
  // Give up if too many strings failed to parse or if the parsed value changes when converted back to text
  if ((typeof parsed === "string" && ++unparsed > maxUnparsed) ||
    !this.isEqualFormatted(formatter.formatAny(parsed), value)) {
    return null;
  }
  result.push(parsed);
}
```

**Flow:** Budget computed over non-empty count × 0.1 → per value: blank handled by type's null-storage policy; parse failure increments counter and aborts past budget; parse success must format back (via a formatter built from the guessed colInfo) to the ORIGINAL string.
**Invariant:** Two independent gates, either kills the guess: (1) unparseable fraction > 10% of non-empty values; (2) ANY single value whose formatted form differs from its input — even one lossy row vetoes. Blank handling is per-type: Bool cannot store nulls (they'd silently become false), so a blank column never guesses Bool; everything else maps blanks to null. Numeric relaxes gate 2 by stripping whitespace/LRM chars (`NumberParse.removeCharsRegex`) on BOTH sides before comparing — `"1 234"` may equal `"1234"`.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && sed -n "175,214p" test/common/ValueGuesser.ts | grep -c "check("'` → 5 (nine-ok/eight-reject, each repeated with 90 blanks proving blanks don't inflate the denominator).
Direct tests: `test/common/ValueGuesser.ts` :175–213 ("should require 90% of values to be parsed").

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ValueGuesser maxUnparsed allowBlank isEqualFormatted guess","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the non-empty-denominator budget and per-value round-trip veto verbatim; adapt the 0.1 constant only with tests; omit the formatter-based comparison at your peril — string-equality alone reintroduces the `"1"`→`"1.0"` class of silent corruption.
