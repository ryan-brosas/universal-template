<!-- capsule-v2 -->
# Two-digit-year window override — how do "5/11/68" style years stay in living memory instead of becoming 2068?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What rule maps a two-digit year to a century, and why must it be patched into moment itself?

## parseTwoDigitYear overridden: +2000 unless the result would exceed current year + 10
**Path/Symbol:** `app/common/parseDate.ts`: `TWO_DIGIT_YEAR_THRESHOLD = 10` (:14), `MAX_TWO_DIGIT_YEAR = new Date().getFullYear() + 10 - 2000` (:15), moment override (:18–21).
**Signature:** `(moment as any).parseTwoDigitYear = (yearString: string): number`.
**Data Shape:** Module side effect executed on import — every subsequent moment.tz parse inherits it.

### Decisive source
```ts
export const TWO_DIGIT_YEAR_THRESHOLD = 10;
const MAX_TWO_DIGIT_YEAR = new Date().getFullYear() + TWO_DIGIT_YEAR_THRESHOLD - 2000;

// Moment suggests that overriding this is fine, but we need to force TypeScript to allow it.
(moment as any).parseTwoDigitYear = function(yearString: string): number {
  const year = parseInt(yearString, 10);
  return year + (year > MAX_TWO_DIGIT_YEAR ? 1900 : 2000);
};
```

**Flow:** Any strict-mode format containing YY reaches this hook. Years that land at most 10 years beyond the CURRENT year get +2000 ("30" → 2030 while it's 2026); anything further ahead is assumed historical and gets +1900 ("68" → 1968, not 2068). The comment pins alignment with bootstrap-datepicker's assumeNearbyYear so the datepicker widget and the parser agree.
**Invariant:** The threshold is relative to now, not a fixed pivot — code that snapshots `MAX_TWO_DIGIT_YEAR` at build time drifts. The override must be installed BEFORE any parsing happens; import-order dependence is real but accepted because this module is imported by every parser entry point. A porter using raw moment gets moment's own pivot (currently +50/-49-ish) which disagrees with the datepicker — dates jump decades between UI and stored value.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "parseTwoDigitYear" app/common/parseDate.ts && grep -n "TWO_DIGIT_YEAR_THRESHOLD" app/common/parseDate.ts'` → :18 override and :14 exported constant (reused by tests).
Direct tests: `test/common/parseDate.ts` two-digit-year cases inside `describe("parseDate")` (:98+).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"parseTwoDigitYear TWO_DIGIT_YEAR_THRESHOLD moment","limit":4,"detail":"ids"}'
```

## Verdict
Adopt the year>currentYear+10 ⇒ 1900s rule as a parser-level hook; adapt the mechanism if your host has no global parser object (wrap instead of monkey-patch); omit nothing — the datepicker-agreement invariant is the whole point.
