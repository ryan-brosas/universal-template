<!-- capsule-v2 -->
# DateTime two-stage reassembly — why is "date part, then time" parsed as strict-UTC-date + reformatted string?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How does parseDateTime combine a flexible date with a separately-extracted time without double-applying the timezone?

## Parse date alone at UTC midnight, re-format to YYYY-MM-DD, THEN append time+offset and parse once in the real zone
**Path/Symbol:** `app/common/parseDate.ts`: `parseDateTime` (:180–219), decisive reassembly (:213–218).
**Signature:** `parseDateTime(dateTime: string, options: ParseOptions): number | undefined` (ms→s valueOf/1000).
**Data Shape:** `options = { dateFormat?, timeFormat?, timezone? }`; returns epoch SECONDS.

### Decisive source
```ts
const dateOnly = parseDateStrict(dateTime, dateFormat, undefined, timezone);
if (dateOnly) { return dateOnly; }              // pure date → done
const parsedTimeZone = parseTimeZone(dateTime, timezone);   // peel tz suffix first
...
const parsedTime = standardizeTime(dateTime);   // peel time suffix
if (!parsedTime) return;
dateTime = parsedTime.remaining;
const date = parseDateStrict(dateTime, dateFormat);         // date ALONE, default UTC
if (!date) return;
// date is a timestamp of midnight in UTC, so to get a formatted representation (for parsing
// together with time), take care to interpret it in UTC.
const dateString = moment.unix(date).utc().format("YYYY-MM-DD");
dateTime = dateString + " " + parsedTime.time + tzOffset;
const fullFormat = "YYYY-MM-DD HH:mm:ss" + (tzOffset ? "Z" : "");
return moment.tz(dateTime, fullFormat, true, timezone).valueOf() / 1000;
```

**Flow:** try whole-string-as-date → strip timezone suffix → strip/standardize time → parse remaining date strictly at UTC → RE-SERIALIZE that date as plain `YYYY-MM-DD` → concatenate standardized `HH:mm:ss` plus any explicit offset → single strict parse in the column's timezone.
**Invariant:** The intermediate UTC round-trip prevents the classic double-shift bug: had the date been parsed directly in the target timezone and then combined, midnight would shift by the zone offset when the offset is later applied again via the `Z` suffix. The comment is load-bearing — a porter "simplifying" to one parse produces dates off by hours depending on direction of the offset. Whole-string-first ordering also preserves pure-date fast paths (and raw-timestamp passthrough inside parseDateStrict).
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "moment.unix(date).utc().format" app/common/parseDate.ts && sed -n "211,219p" app/common/parseDate.ts | grep -c "tzOffset"'` → :215 round-trip line; 2 uses of tzOffset in the tail.
Direct tests: `test/common/parseDate.ts` datetime cases in :98+ suite (date+time+zone combos).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"parseDateTime standardizeTime utc format reassembly","limit":4,"detail":"ids"}'
```

## Verdict
Adopt the split-parse/reassemble choreography exactly; adapt formats if your storage differs from epoch-seconds; omit nothing — every step guards a distinct corruption class.
