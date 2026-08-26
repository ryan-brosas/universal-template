<!-- capsule-v2 -->
# Strict-vs-lenient date parsing duality — why do paste/import and cell-entry use different date parsers?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** Which fallback format set applies in each entry path, and why must bulk import be stricter than interactive entry?

## parseDate falls back to ALL PARSER_FORMATS; parseDateStrict only to UNAMBIGUOUS_FORMATS
**Path/Symbol:** `app/common/parseDate.ts`: `PARSER_FORMATS` (:30–60), `UNAMBIGUOUS_FORMATS` (:62–65), `parseDate` (:106–143), `parseDateStrict(date, dateFormat, results?, timezone)` (:153–178).
**Signature:** `parseDateStrict(...): number | undefined` (seconds since epoch, or undefined); collects ALL matches into `results?: Set<number>` when provided.
**Data Shape:** Formats are moment strings; strict mode (`true`) always on.

### Decisive source
```ts
export function parseDateStrict(
  date: string, dateFormat: string | null, results?: Set<number>, timezone: string = "UTC",
): number | undefined {
  ...
  const dateFormats = [..._buildVariations(dateFormat, date), ...UNAMBIGUOUS_FORMATS];
  const cleanDate = date.replace(SEPARATORS, " ").trim();
  for (const format of dateFormats) {
    const m = moment.tz(cleanDate, format, true, timezone);
    if (m.isValid()) {
      const value = m.valueOf() / 1000;
      if (results) { results.add(value); } else { return value; }
    }
  }
}
```
with:
```ts
const UNAMBIGUOUS_FORMATS = [
  "YYYY M D",
  ...PARSER_FORMATS.filter(f => f.includes("MMM")),
];
```

**Flow:** Both entries prepend variations of the column's own format (`_buildVariations`) before their fallback list. Lenient path then tries numeric-month orders like `D M YYYY` — fine for one interactive cell where the user sees the result. Bulk paste uses the strict path: numeric day/month swaps ("03/04" as Mar 4 vs Apr 3) are exactly the silent corruption class it exists to prevent; month-NAME formats (`MMM`) carry no such ambiguity.
**Invariant:** UNAMBIGUOUS = ISO order plus every month-name format. The `results` Set variant returns undefined-with-populated-set semantics: callers detect "multiple plausible dates" by set size instead of receiving an arbitrary first match. A porter who "simplifies" by sharing one format list reintroduces silent day/month swapping at import scale.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && sed -n "62,65p" app/common/parseDate.ts && grep -n "results.add(value)" app/common/parseDate.ts'` → filter-to-MMM definition and :172.
Direct tests: `test/common/parseDate.ts` :98 `describe("parseDate")`, :449 `describe("guessDateFormat")` — strict/lenient split pinned throughout.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"parseDateStrict UNAMBIGUOUS_FORMATS PARSER_FORMATS moment strict","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the two-list split and the collect-all-matches Set API; adapt format lists to your locales (keep the month-name-only rule for the safe set); omit `results` only if no caller needs ambiguity detection.
