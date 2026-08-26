<!-- capsule-v2 -->
# Overlay pushState trigger — how do I open LinkedIn's contact-info overlay deterministically without clicking through the UI?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** can the contact-info modal be summoned by URL state alone, and what must be captured BEFORE the history dance?

## extractEmail flow — snapshot location.href, double-pushState + back, then parse the modal
**Path/Symbol:** `lib/linkedin/linkedin.email.service.ts:LinkedinEmailService.process` (:16–47, the pushState block :31–38); parser `lib/linkedin/linkedin.abstract.service.ts:LinkedinAbstractService.extractEmail` (:9–114); loader wait `waitForLoader` (:455–467).
**Signature:** `process(page, cdp, {url}) -> {email?, phone?, websites?, twitter?, im?, birthDay?, url, linkedin_id}` (missing sections are simply absent keys).
**Data Shape:** contact fields parsed from `.artdeco-modal` — email via regex over ALL modal text; phone/im/websites rows as `{value, type}` pairs located by icon-type attribute (`[type="phone-handset-icon"]`, `[type="speech-bubble-icon"]`, `[type="link-icon"]`) with legacy class fallbacks (`.ci-phone`, `.ci-ims`, `.ci-websites`); birthday/twitter single strings; `linkedin_id` = canonical `/in/<slug>` from the PRE-overlay URL.

### Decisive source
```ts
gotoUrl(page, theUrl); await this.waitForLoader(page); await timer(3000);
const newUrl = await page.evaluate(() => window.location.href); // CAPTURE FIRST — see comment:
// "this is super important, if we don't do this, we would not know about the new url
//  And we will not know about connection requests approved"
await page.evaluate(() => {
  history.pushState({}, '', window.location.href + 'overlay/contact-info/');
  history.pushState({}, '', window.location.href + 'overlay/contact-info/');
  history.back();
});                                   // SPA router mounts the overlay WITHOUT any click
return {...await this.extractEmail(page), url: theUrl,
        linkedin_id: createLinkedinLink(newUrl, false)};
// catch: return {url, linkedin_id} — identity is returned even when extraction dies
```

**Flow:** canonicalize URL (`createLinkedinLink`) → goto with timeout:0 + loader-clearance wait → snapshot final href (redirects may have moved /in/ → /in/overlay or logged you elsewhere) → in-page history trick pushes the overlay route twice and pops once → LinkedIn's router renders `.artdeco-modal` → parser reads it → identity + contacts returned together; ANY throw still returns `{url, linkedin_id}`.
**Invariant:** capture `window.location.href` BEFORE mutating history — post-redirect identity is only knowable at that moment; the overlay is opened by ROUTE STATE, so no UI locator can rot underneath this approach. The double-push+back is load-bearing (matches LinkedIn's own overlay navigation depth); a single push leaves the history stack in a different shape.
**Probe:** no upstream tests — caveat recorded; boundary verified by reading email/visit services + abstract parser at HEAD; graph anchors resolve: `LinkedinEmailService.process` :16–47, `extractEmail` :9–114. Runner-up consumer of the same identity pattern: visit.service.ts (:15–35) returns `{url, linkedin_id}` after goto+loader.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "pushState overlay contact-info extractEmail", limit: 5 });
// resolves LinkedinEmailService.process :16–47 + LinkedinAbstractService.extractEmail :9–114
```

## Verdict
Adopt the pre-capture href snapshot + pushState/back overlay summon + always-return-identity error contract; adapt field parsing to current DOM (icon-type selectors rot); omit linvo's fixed 10 s sleep inside extractEmail (replace with the loader-clearance wait). Contrast: tabbed-overlay-section-walking CLICKS into the contact dialog and walks headings interactively; this seam skips interaction entirely by driving the SPA router — prefer route-state when you control navigation, clicking when you inherit a live session mid-page.
