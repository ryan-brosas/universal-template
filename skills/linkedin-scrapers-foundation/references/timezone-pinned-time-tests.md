<!-- capsule-v2 -->
# Timezone-pinned time tests — how do NOW-anchored date assertions stay reproducible across laptops and CI?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** Where must the timezone be fixed so 'Present'→now() formatting and inclusive day-diff assertions are deterministic?

## Pin the zone before the first assertion
**Path/Symbol:** `src/utils/index.test.ts:1–5` (import + `moment.tz.setDefault('Europe/Amsterdam')`); kernel under test `src/utils/index.ts:formatDate` (:30–36) and `getDurationInDays` (:38–42).
**Signature:** `moment.tz.setDefault(tzName)` executed at the TOP of the test module, before any describe body runs.
**Data Shape:** `formatDate('Present')` returns `moment().format()` — an ISO string carrying the LOCAL offset; explicit-date assertions compare full offset-bearing strings (`'2020-12-31T01:11:00+01:00'`).

### Decisive source
```ts
// Make sure our CI uses the same timezone
import moment from 'moment-timezone'
moment.tz.setDefault('Europe/Amsterdam');
...
it('should return a formatted date', () => {
  const formattedDate = formatDate(new Date('2020-12-31T01:11:00+01:00'));
  expect(formattedDate).toBe('2020-12-31T01:11:00+01:00')
})
```

**Flow:** import moment-timezone → setDefault zone → only now are formatted-string assertions stable: moment renders in the DEFAULT zone unless a call overrides it; without the pin, a UTC CI machine and a CET laptop disagree on offset suffixes (and on what "today" is for Present/duration math).
**Invariant:** every assertion whose input or expectation contains NOW must execute under a pinned zone, and the pin lives IN THE TEST FILE itself so runner/config drift cannot silently drop it. Pairs with `duration-with-present`: production anchors 'Present' at FORMAT time — the test pin fixes WHERE that anchor sits.
**Probe:** `src/utils/index.test.ts` — pure-function suite, executable without a browser (executed green this pass via staged deps; evidence in the work record verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "formatDate getDurationInDays moment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt test-file-local zone pinning for ANY now()-dependent normalizer (durations, "time ago", schedule windows); adapt the zone choice — prefer explicit UTC in new suites unless matching a legacy baseline like this repo's Amsterdam default; omit nothing. Generalizes far past LinkedIn: any scraper computing time against 'now'.
