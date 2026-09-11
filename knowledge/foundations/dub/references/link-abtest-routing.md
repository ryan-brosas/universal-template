<!-- capsule-v2 -->
# A/B test variant routing — how do weighted link variants get sticky assignment without server-side session state?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** How is a visitor's variant chosen, made sticky across clicks, and expired when the test window closes?

## resolveABTestURL weighted draw + cookie stickiness
**Path/Symbol:** `apps/web/lib/middleware/utils/resolve-ab-test-url.ts:resolveABTestURL` (8-64); stickiness write `apps/web/lib/middleware/utils/create-response-with-cookies.ts:26-31`; consumption in `apps/web/lib/middleware/link.ts:156-161`.
**Signature:** `resolveABTestURL({testVariants?: {url, percentage}[], testCompletedAt?: Date}): Promise<string | null>`.
**Data Shape:** `testVariants` length ∈ [2, MAX_TEST_COUNT]; each `{url: string, percentage: number}`; percentages are relative weights (need not sum to 100); sticky cookie `dub_test_url`, 1-week maxAge.

### Decisive source
```ts
// gate 1: only live tests route
if (!testVariants || !testCompletedAt ||
    !(new Date(testCompletedAt) > new Date())) return null;

// gate 2: cardinality guard
if (testVariants.length < 2 || testVariants.length > MAX_TEST_COUNT) {
  console.error(`Invalid test count: ${testVariants.length} for link.`);
  return null;
}

// stickiness: returning visitors keep their variant
const urlFromCookie = cookieStore.get("dub_test_url")?.value;
if (urlFromCookie && testVariants.map((t) => t.url).includes(urlFromCookie)) {
  return urlFromCookie;
}

// weighted draw via cumulative weights
let i = 0;
const weights = [testVariants[0].percentage];
for (i = 1; i < testVariants.length; ++i)
  weights[i] = testVariants[i].percentage + weights[i - 1];
const random = Math.random() * weights[weights.length - 1];   // scaled to weight SUM
for (i = 0; i < weights.length; ++i) if (weights[i] > random) break;
return testVariants[i].url;
```

**Flow:** middleware calls it BEFORE reading `cachedLink.url`; a non-null result REPLACES the destination (`const url = testUrl || cachedLink.url`) and flows into every downstream branch → the chosen URL rides back to the browser as the week-long `dub_test_url` cookie → next click short-circuits to the same URL while it remains a member of the CURRENT variant set.
**Invariant:** whole function is fail-open — any throw returns `null` and traffic falls through to the default destination. Stickiness validates membership against today's variant list, so editing a variant set safely re-draws stale visitors. Random is scaled by the weight SUM, not by 100. The completed-test check uses strict `>` — at exactly `testCompletedAt` the test is over.
**Probe:** no upstream unit test (coverage caveat). Deterministic probe: with weights `[10, 90]` over N draws, assert both URLs appear and ratio trends toward 1:9; assert cookie value reuse when still in the set; assert null after `testCompletedAt`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "resolveABTestURL testVariants dub_test_url", limit: 10 });
```

## Verdict
Adopt: cumulative-weight draw scaled to sum, cookie stickiness validated against current membership, fail-open error handling, two-gate entry (live window + cardinality). Adapt storage of variants and stickiness duration; consider deterministic hashing instead of Math.random if cross-device consistency matters. Omit the completion cron (`complete-ab-tests.ts`) unless you auto-close tests.
