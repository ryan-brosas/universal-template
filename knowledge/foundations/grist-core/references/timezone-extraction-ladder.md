<!-- capsule-v2 -->
# Time & timezone extraction ladder — how does "3/4/2026 5pm EST +0230" become one timestamp?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** In what order are UTC markers, numeric offsets, zone abbreviations and am/pm handled, and what happens when only an abbreviation is found?

## parseTimeZone tries UTC → numeric offset → zone abbreviation (stripped, NOT applied); standardizeTime hand-parses HH[:MM[:SS]][am|pm]
**Path/Symbol:** `app/common/parseDate.ts`: `TIME_REGEX` (:67), `UTC_REGEX` (:69), `NUMERIC_TZ_REGEX` (:70), `tzAbbreviations` memoized builder (:75–85), `parseTimeZone` (:288–316), `standardizeTime` (:321–337).
**Signature:** `parseTimeZone(str, timezone): { remaining: string, tzOffset: string }`; `standardizeTime(timeString): { remaining, time } | undefined`.
**Data Shape:** `tzOffset` is "" or a `±HH:MM` literal appended to the datetime string; abbreviation matches leave it EMPTY.

### Decisive source
```ts
let tzMatch = UTC_REGEX.exec(str);            // [^a-zA-Z](UTC?|GMT|Z)$  → "+00:00"
...
} else {
  tzMatch = NUMERIC_TZ_REGEX.exec(str);       // ([+-]\d\d?)(?::?(\d\d))?$ → calculateOffset pads to ±HH:MM
  if (!tzMatch && timezone) {
    // Abbreviations are simply stripped and ignored, so tzOffset is not set in this case
    tzMatch = tzAbbreviations(timezone).exec(str);   // abbreviations OF THE COLUMN'S ZONE ONLY
  }
}
...
// TIME_REGEX = /(?:^|\s+|T)(\d\d?)(?::(\d\d?)(?::(\d\d?))?)?|(\d\d?)(\d\d)\s*([ap]m?)?$/i
if (hours < 12 && hours > 0 && ampm.startsWith("p")) hours += 12;
else if (hours === 12 && ampm.startsWith("a")) hours = 0;
```

**Flow:** UTC/GMT/Z ⇒ fixed `+00:00` offset. `+5`, `-0330` style ⇒ normalized via `calculateOffset` (`sign + hh.padStart(2) + ":" + mm.padStart(2)`). Zone ABBREVIATIONS (EST, CET…) valid only for the document's own timezone — matched from `moment.tz.zone(tz).abbrs`, then STRIPPED with empty offset so the value is interpreted AS the column's timezone rather than re-zoned. Time part handles compact `1832` (match[4][5]) plus am/pm edge rules: `12pm`=12h, `12am`=0h, `0am` stays 0.
**Invariant:** Abbreviation ≠ conversion — the `[ap]m` regex guard `[^a-zA-Z]` prevents "CEST" matching its tail "EST". Offsets are appended as text and carried into the moment format as `Z` (`timeformat = " HH:mm:ss" + (tzOffset ? "Z" : "")`). Anything left unparsed after standardizeTime (residual text) makes parseDate bail null — no silent truncation.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "abbreviations are simply stripped" app/common/parseDate.ts -i && grep -n "hours === 12 && ampm.startsWith" app/common/parseDate.ts'` → :303 comment and :332 midnight rule.
Direct tests: `test/common/parseDate.ts` timezone/time cases within :98+ suite (incl. abbreviation stripping).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"parseTimeZone standardizeTime NUMERIC_TZ_REGEX tzAbbreviations","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the three-rung ladder and the strip-don't-rezone abbreviation rule; adapt abbreviation source to your tz database; omit the compact-HHMM branch only if your inputs never contain it (tests will tell you).
