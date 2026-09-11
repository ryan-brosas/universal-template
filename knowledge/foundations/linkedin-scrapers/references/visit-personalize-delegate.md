<!-- capsule-v2 -->
# Visit-personalize-delegate composition — how do I compose an action service from existing services, deriving its data by visiting the page first?

**Source:** linvo-scraper ISC `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** How does a higher-level action (message-after-viewing-profile) reuse the message service while sourcing fresh profile data at run time — and how does it refuse when the relationship precondition fails?

## The composite
**Path/Symbol:** `lib/linkedin/linkedin.message.with.view.ts:LinkedinMessageWithView.process` (:24–63); implements the SAME `LinkedinServicesInterface<RequiredData>` as every leaf service (linvo-service-taxonomy).
**Signature:** `process(page, cdp, data: { url, message, contact, IgnoreProspectMessages, extra }) -> Promise<string>` (delegates to `LinkedinMessageService.process`).
**Data Shape:** input needs only a profile URL + template + sender identity (`extra.myname/mylastname/mycompany`) — everything else is DERIVED by visiting.

### Decisive source
```ts
const theUrl = createLinkedinLink(data.url, true);
gotoUrl(page, theUrl);
await this.waitForLoader(page);
await page.waitForSelector(".pv-top-card--list > li, .pv-top-card__photo");
await timer(3000);
const info = await this.extractInformation(page);
const newMessage = await this.generateMessage(data.message, { firstName: info.name, ...data.extra });

const url = await page.evaluate(() => {
  return Array.from(document.body.querySelectorAll("*"))
    ?.find((p) => p?.getAttribute("href")?.indexOf("/messaging/thread")! > -1)
    ?.getAttribute("href");
});
if (!url) throw new LinkedinErrors("You are not connected with the prospect");

return new LinkedinMessageService().process(page, cdp, { ...data, url, info: {...}, message: newMessage });
```

**Flow:** canonicalize URL → navigate + wait for top-card selector → humanize pause (`timer(3000)`) → scrape name/company/photo in-page → render the template with LIVE data merged over caller `extra` → probe the DOM for ANY `/messaging/thread` href (existence of a message thread ⇒ connected) → MISSING thread ⇒ typed `LinkedinErrors("You are not connected with the prospect")` → otherwise delegate to the plain message service with the enriched payload.
**Invariant:** the `/messaging/thread` href-probe is a cheap PRECONDITION CHECK that replaces an API call — if no thread exists, sending would fail mid-composition downstream, so it fails EARLY with a typed, schedulable error. Data flows one way: leaf services stay ignorant of where their inputs came from; composites own acquisition. The 3s timer after load mirrors linvo's humanization discipline even before any interaction.
**Probe:** no dedicated spec for MessageWithView (coverage caveat: source-read at pinned HEAD cfbe910); the delegated-into message service IS pinned by message-send-guard-chain's probes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "LinkedinMessageWithView process", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape: composites = acquire-by-visiting + derive + guard + delegate; leaves = pure action executors. Adapt the precondition probe to your platform's relationship artifact. Omit the specific selectors (page-version-bound).
