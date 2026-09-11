<!-- capsule-v2 -->
# Format-guess tie-breaking & partial-format defaults — how is ONE date format chosen for a column, and how do "3/1978"-style inputs still parse?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** When several formats fit the data equally, which wins, and how does parsing survive inputs missing pieces of the chosen format?

## guessDateFormat picks lexicographic-last among tied formats; _getPartialFormat drops Y then M from the pattern when input has fewer parts
**Path/Symbol:** `app/common/parseDate.ts`: `guessDateFormat` (:345–351), `guessDateFormats` (:358–394), `_getPartialFormat` (:225–246), `_buildVariations` (:251–279).
**Signature:** `guessDateFormat(values, timezone="UTC"): string` (returns `"YYYY-MM-DD"` when nothing fits).
**Data Shape:** Candidate set capped: >10 distinct guesses ⇒ give up (`null`); sample capped at 100 distinct strings.

### Decisive source
```ts
// guessDateFormat
const formats = guessDateFormats(values, timezone);
if (!formats) return "YYYY-MM-DD";
return last(formats)!;      // formats are SORTED lexicographically → last tie wins

// guessDateFormats scoring loop
for (const format of formatKeys) {
  for (const dateString of dateStrings) {
    const m = moment.tz(dateString, format, true, timezone);
    if (m.isValid()) formats[format] += 1;
  }
}
const maxCount = Math.max(...Object.values(formats));
return formatKeys.filter(format => formats[format] === maxCount).sort();

// _getPartialFormat: input "3" against format "M D YYYY" → strip year first, then month
```

**Flow:** moment-guess proposes candidates per sampled value → >10 distinct candidates aborts guessing (returns default) → each candidate scored by how many FULL column values parse under it (strict mode) → all top scorers returned sorted; `guessDateFormat` takes the LAST — deliberately favouring early-Y/early-M layouts "to match the old dateguess.py", keeping behaviour stable across the rewrite.
**Invariant:** Tie-break is lexicographic-last, NOT insertion order or first-match — a porter "cleaning this up" changes which format thousands of columns display with. Partial-input support comes from REMOVING trailing parts of the FORMAT (year first, then month) rather than relaxing strict mode, so defaults fill from moment's "current time" semantics deterministically (current year preferred over current month). `_buildVariations` additionally appends ` YYYY` when the column format lacks one but inputs end in a 4-digit year.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && sed -n "345,351p" app/common/parseDate.ts && grep -n "formatKeys.length > 10\|getDistinctValues(dateStrings, 100)" app/common/parseDate.ts'` → last-tie return plus both caps (:377, :360).
Direct tests: `test/common/parseDate.ts` :449 `describe("guessDateFormat")` — tie ordering pinned.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"guessDateFormat guessFormat tie lexicographic partial","limit":5,"detail":"ids"}'
```

## Verdict
Adopt candidate-cap/score/tie rules verbatim (they pin UI-visible behavior); adapt the candidate generator (moment-guess) to any equivalent proposer; omit the lexicographic rule only if you accept silent display churn across ports.
