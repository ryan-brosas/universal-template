<!-- capsule-v2 -->
# Visit-resolve identity — why must "visiting" return the URL LinkedIn REDIRECTED to, not the URL you asked for?

**Source:** linvo-scraper ISC `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what makes a visit action usable as an identity-resolution step for later outreach actions?

## Visit is a resolver, not just navigation
**Path/Symbol:** `lib/linkedin/linkedin.visit.service.ts:LinkedinVisitService.process` (:15-35).
**Signature:** `process(page, cdp, data: { url })` → `Promise<{ url: string; linkedin_id }>` where `linkedin_id = createLinkedinLink(newUrl, false)`.
**Data Shape:** input url may be bare (`/in/slug`) or absolute; output carries BOTH the requested url and the canonical id extracted from the POST-REDIRECT location.

### Decisive source
```ts
const theUrl =
  url.indexOf("linkedin.com") !== -1 ? url : `https://www.linkedin.com${data.url}`;
gotoUrl(page, theUrl);
await this.waitForLoader(page);
await page.waitForSelector(".pv-top-card--list > li, .pv-top-card__photo");
await timer(3000);
// this is super important, if we don't do this, we would not know about the new url
// And we will not know about connection requests approved
const newUrl = await page.evaluate(() => window.location.href);
return {url: theUrl, linkedin_id: createLinkedinLink(newUrl, false)};
```

**Flow:** absolutize bare paths → goto → loader wait → profile-card selector → settle timer(3000) → re-read `window.location.href` AFTER settle → canonicalize THAT into linkedin_id. The in-source comment marks the redirect-read as load-bearing: LinkedIn redirects renamed/removed profiles to alternates and flips pending-connection states during navigation — the post-settle href is the ground truth.
**Invariant:** identity comes from the post-redirect `window.location.href`, never from the requested URL; the settle timer precedes the read (read-before-settle races the client-side redirect). Every downstream consumer keys on `linkedin_id`.
**Probe:** no repo tests (coverage caveat: source-grounded only); graph probe resolves `LinkedinVisitService.process` at lib/linkedin/linkedin.visit.service.ts :15-35.
**Retrieve:** `search_graph({project:"linvo-scraper", query:"LinkedinVisitService process", limit:6})`.

## Verdict
Adopt visit-as-resolver (post-settle href read-back → canonical identity) for any portal that redirects on state change. Adapt selectors/timers. Omit nothing behavioral. Pairs with `visit-personalize-delegate` (which composites ON this service).
