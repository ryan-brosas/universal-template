<!-- capsule-v2 -->
# Duration-with-present — how do I compute "time in role" when the end date may be literally "Present"?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** Where do the Present-case branches live so closed-date math stays honest?

## endDateIsPresent flag + dual duration branches
**Path/Symbol:** `src/index.ts` experience mapping (:674–695) over parser (:647–652); date kernel in `src/utils/index.ts:formatDate` (:30–36) + `getDurationInDays` (:38–42); same pattern re-decided in volunteer parsing (:777–781).
**Signature:** `formatDate(date): string` ('Present' → `moment().format()`, else `moment(date,'MMMY').format()`); `getDurationInDays(start, end): number | null` (+1 day inclusive count, null on missing inputs).
**Data Shape:** raw range text split on EN DASH `–`: `startDatePart.trim()`, `endDatePart.trim().toLowerCase() === 'present' || false` → boolean carried alongside dates through Raw→clean.

### Decisive source
```ts
const startDate = formatDate(rawExperience.startDate);
const endDate = formatDate(rawExperience.endDate) || null;
const endDateIsPresent = rawExperience.endDateIsPresent;

const durationInDaysWithEndDate = (startDate && endDate && !endDateIsPresent)
  ? getDurationInDays(startDate, endDate) : null
const durationInDaysForPresentDate = (endDateIsPresent && startDate)
  ? getDurationInDays(startDate, new Date()) : null
const durationInDays = endDateIsPresent ? durationInDaysForPresentDate : durationInDaysWithEndDate;
```

**Flow:** parse splits the en-dash range and derives `endDateIsPresent` ONCE at the boundary → 'Present' formats to NOW at clean time (so durations drift correctly with scrape time) → duration picks exactly one of two branches; both guard on input presence and yield null otherwise → the boolean rides along in the output schema so downstream consumers can distinguish open from closed ranges.
**Invariant:** the Present decision happens at PARSE time (string comparison) but the NOW-anchor happens at FORMAT time — separating these keeps 'Present' semantics consistent across sections (experiences :651, volunteer :778 duplicate the identical split logic deliberately). Inclusive counting (+1) matches human expectations for tenure. Missing start OR end ⇒ null duration, never NaN.

### Named trap — flag vs sentinel diverge on missing end-date markup
The raw ternary `(endDatePart && !endDateIsPresent) ? endDatePart.trim() : 'Present'` (:651–652 experiences, :777–779 volunteer) defaults a MISSING end-date element to `endDate = 'Present'` while `endDateIsPresent` stays FALSE. Node-side, `formatDate` special-cases the STRING `'Present' → moment().format()` (utils :31–33) regardless of the flag — so the boolean and the magic string disagree exactly when the DOM node is absent: `durationInDaysWithEndDate`'s guard (`startDate && endDate && !endDateIsPresent`) passes and `getDurationInDays(startDate, NOW)` fabricates a to-today tenure for what may be an already-ended role with broken markup. Port rule: reconcile flag AND sentinel at ONE boundary (derive the boolean FROM the defaulted string, or default to null), never let two mechanisms own the same decision. Adjacent hazard, same lines: any non-'Present' text failing `moment(date,'MMMY')` formats to the truthy string `"Invalid date"` and flows into `getDurationInDays` unguarded (its only guard is null/empty).
**Probe:** `src/utils/index.test.ts::describe('formatDate')` / `describe('getDurationInDays')` — pins 'Present'→now formatting and the +1 inclusive diff without any live data.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "formatDate getDurationInDays endDateIsPresent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the carry-the-flag pattern (boolean decided once, threaded through serialization) plus the two-branch duration selection for any CV/job-history schema. Adapt date formats and the now-anchor policy to your domain. Omit the duplicated inline re-parsing if your language allows shared helpers — upstream duplicates it because browser-context closures can't import utils.
