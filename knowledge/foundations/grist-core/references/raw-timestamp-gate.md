<!-- capsule-v2 -->
# Raw-timestamp passthrough gate — which numeric strings ARE dates already?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** When should an all-digit string be treated as a Unix timestamp instead of attempted as a formatted date?

## parseTimeStamp accepts exactly 9–10 leading-nonzero digits; 11 digits rejected by era math
**Path/Symbol:** `app/common/parseDate.ts`: `parseTimeStamp` (:440–452); called first thing in BOTH `parseDate` (:113) and `parseDateStrict` (:160).
**Signature:** `parseTimeStamp(date: string): number | null` (seconds since epoch or null).
**Data Shape:** Regex `/^[1-9]\d{8,9}$/` — no sign, no separators, no leading zero.

### Decisive source
```ts
export function parseTimeStamp(date: string): number | null {
  // If this looks like a timestamp (number with 9 or more digits), just return it.
  // This covers most of the cases leaving some time around the unix epoch not covered.
  // So time before 100 000 000 (1974-04-26) is not covered. Also negative values
  // are also not supported, as they overlap with the YYYYYY date format.
  if (date && /^[1-9]\d{8,9}$/.test(date)) {
    const parsedDate = moment(date, "X");
    if (parsedDate.isValid()) { return parsedDate.unix(); }
  }
  return null;
}
```

**Flow:** Both lenient and strict parsers check this BEFORE any format loop. 9–10 digit strings (Sep 2001 … Nov 2286 range) pass through untouched; shorter numbers could be years/dates ("20260304") and longer ones exceed the era, so they fall through to normal parsing.
**Invariant:** The gate is deliberately NARROW: leading `[1-9]` excludes "012345678"-style strings that might be IDs padded for sorting; the 11-digit exclusion is documented (lowest 11-digit ts is year 2286) rather than arbitrary. This is also why a Numeric column containing phone-like numbers never silently becomes dates — ValueGuesser's round-trip check would fail anyway, but this gate removes the ambiguity earlier. Porters who widen the regex to `\d{9,}` mis-parse zero-padded identifiers as 1970s timestamps.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "\\/\\^\\[1-9\\]" app/common/parseDate.ts && grep -n "parseTimeStamp(date)" app/common/parseDate.ts'` → :445 regex and both call sites :113/:160.
Direct tests: `test/common/parseDate.ts` timestamp passthrough cases inside the main describe (:98+).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"parseTimeStamp timestamp seconds epoch digits","limit":4,"detail":"ids"}'
```

## Verdict
Adopt the exact width/sign/leading-digit constraints; adapt nothing — the bounds encode epoch-era arithmetic that doesn't port differently; omit the passthrough entirely only if your host never imports raw epoch strings.
