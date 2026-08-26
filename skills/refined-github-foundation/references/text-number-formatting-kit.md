<!-- capsule-v2 -->
# text-and-number-formatting-kit — how do you render counts, plurals, and loose numbers from scraped DOM the same way the host does?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What are the repo's canonical formatting primitives, their exact rounding/abbreviation behavior, and the DOM-number-extraction rule?

## abbreviateNumber — lowercased K/M/B with no padding
**Path/Symbol:** `source/helpers/abbreviate-number.ts:abbreviateNumber` (:3–5).
**Signature:** `abbreviateNumber(number: number, digits = 1): string`.
**Data Shape:** Delegates to `js-abbreviation-number` with `{padding: false}` then `.toLowerCase()` — so `1200 → '1.2k'` not `'1.2K'`; GitHub renders lowercase.
**Probe:** No direct unit test; trivial wrapper. (Caveat recorded.)

## pluralize — $$-templated count interpolation
**Path/Symbol:** `source/helpers/pluralize.ts:pluralize` (:15–30).
**Signature:** `pluralize(count: number, single: string, plural = single + 's', zero?: string): string`.
### Decisive source
```ts
if (count === 0 && zero) return zero.replace('$$', '0');
if (count === 1) return single.replace('$$', '1');
return plural.replace('$$', String(count));
```
**Invariant:** The count is injected ONLY via `$$` substitution — templates that forget `$$` lose the number silently; `zero` wins over `plural` at 0 only when provided. Default plural is naive `+s`.
**Probe:** `source/helpers/pluralize.test.ts:5–11`: 0-with-zero-form, 0-without (falls to plural "0 numbers"), 1→single, 2→`$$ numbers`, custom plural form.

## abbreviateString / looseParseInt / calculateCssCalcString
**Path/Symbol:** `source/helpers/abbreviate-string.ts:abbreviateString` (:6–10); `source/helpers/loose-parse-int.ts:looseParseInt` (:32–42); `source/helpers/calculate-css-calc-string.ts:calculateCssCalcString` (:51–54).
**Signature:** `abbreviateString(string: string, length: number): string` (slice + `…`, no-op under length); `looseParseInt(text: ChildNode | string | undefined | null): number`; `calculateCssCalcString(string: string): number`.
### Decisive source (the extraction rule)
```ts
return Number(text.replaceAll(/\D+/g, '')); // strip EVERYTHING non-digit, then Number()
```
```ts
const addends = string.split('+').map(part => looseParseInt(part)); // calc() → px addends sum
```
**Invariant:** `looseParseInt` accepts a TEXT NODE directly (`textContent` fallback), returns 0 for null/empty, and strips all non-digits — `'1,234' → 1234`, `'5000+ issues' → 5000`. It is NOT parseInt: no leading-token stop, negatives destroyed. `calculateCssCalcString` exists because `calc()` with custom properties is NOT evaluated by `getComputedStyle()` — it sums px-only addends by abuse of looseParseInt.
**Probe:** `source/helpers/loose-parse-int.test.ts:5–9` ('1,234', 'Bugs 1,234', '5000+ issues'); `source/helpers/calculate-css-calc-string.test.ts:5–9` incl. the joke case `calc(1% / 1em) === 11` proving only px sums are real.

## matchesAnyPattern — string|RegExp|predicate matcher
**Path/Symbol:** `source/helpers/matches-any-patterns.ts:matchesAnyPattern` (:63–78).
**Signature:** `matchesAnyPattern(target: string, patterns: Array<string | RegExp | ((x: string) => boolean)>): boolean`.
**Invariant:** strings compare FULL-equality (`===`), not substring; regexes unanchored; `.some` short-circuits. Callers mixing literal+pattern lists avoid regex-escaping literals.
**Probe:** No dedicated test file; exercised via feature call sites. (Caveat recorded.)

## Verdict
Adopt the whole kit for host-faithful UI text in any ported feature: lowercase abbreviated counts, `$$`-template plurals, DOM-scraped number parsing, px-only calc() evaluation, mixed matcher lists. Adapt abbreviation thresholds/digits and plural word forms per host locale conventions; keep the parse rules EXACT — they encode GitHub's rendered formats.
