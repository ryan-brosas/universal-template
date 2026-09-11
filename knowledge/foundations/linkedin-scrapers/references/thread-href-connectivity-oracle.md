<!-- capsule-v2 -->
# Thread href connectivity oracle — how do I prove "I can message this person" and obtain the conversation URL without opening messaging?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what single in-page probe both gates the send on an existing connection AND supplies the thread URL the sender needs?

## LinkedinMessageWithView.process — whole-body href scan as connection oracle + identity precedence
**Path/Symbol:** `lib/linkedin/linkedin.message.with.view.ts:LinkedinMessageWithView.process` (:35–83; oracle :54–64, delegation :66–82); `RequiredData` (:12–29).
**Signature:** `process(page: Page, cdp: CDPSession, data: RequiredData): Promise<SendResult>` where RequiredData = `{url, message, contact: any, IgnoreProspectMessages: 1|2|0, extra: {myname, mylastname, mycompany}, image?: {todo: "gif"|"upload"|"personalized", value: {picture, id}}}`.
**Data Shape:** oracle output = first href on the page containing `/messaging/thread` (string) or undefined; identity precedence `data?.contact?.name || info.name + " " + info.last_name` applied to BOTH `info.name` and top-level `name`; template context = live top-card fields (`firstName/lastName/companyName/profilePicture`) spread with `data.extra`.

### Decisive source
```ts
const url = await page.evaluate(() => {
  return Array.from(document.body.querySelectorAll("*"))
    ?.find((p) => p?.getAttribute("href")?.indexOf("/messaging/thread")! > -1)
    ?.getAttribute("href");
});

if (!url) {
  throw new LinkedinErrors("You are not connected with the prospect"); // typed, schedulable
}

const messageService = new LinkedinMessageService();
return messageService.process(page, cdp, {
  ...data,
  url,                    // <- the FOUND thread href replaces the input profile url
  info: { /* projected live top-card fields */ name: data?.contact?.name || info.name + " " + info.last_name, url: theUrl },
  name: data?.contact?.name || info.name + " " + info.last_name,
  message: newMessage,    // rendered BEFORE the oracle: template from live visit data
});
```

**Flow:** canonicalize profile URL (`createLinkedinLink(url, true)`) → fire-and-forget goto + loader latch (loader-latch-navigation-kernel) → wait top-card → `extractInformation` reads live fields → `generateMessage` renders the template NOW (visit-personalize-delegate order) → oracle scan → miss throws typed not-connected error (scheduler routes/pauses via LinkedinErrors contract) → hit delegates to the singular message service with the thread href AS `url`, projected `info`, and contact-name-overridden identity.
**Invariant:** connectivity is proven by EXISTENCE of a thread link anywhere in the DOM — no click, no navigation to /messaging, no API call; the found href is authoritative for delivery while the ORIGINAL canonicalized profile URL is preserved separately in `info.url` so audit rows still point at the profile. The template is rendered from the visited page's own data before any gating, so a gated-out run has still paid only one page load.
**Probe:** no upstream test runner exists at pin — recorded BLOCK; deterministic anchors executed instead: `grep -n '"/messaging/thread"' lib/linkedin/linkedin.message.with.view.ts` pins :57; `grep -n "You are not connected" …` pins :63; `grep -n "data?.contact?.name || info.name" …` pins BOTH :77 and :80.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "LinkedinMessageWithView process messaging thread generateMessage extractInformation", limit: 8 });
```

## Verdict
Adopt existence-of-artifact oracles: when a platform renders a deep-link affordance for privileged actions, scanning for that affordance is cheaper and more honest than probing action UIs; adapt the marker substring per surface (`/messaging/thread` here — rot-prone) and consider scoping `querySelectorAll("*")` to containers if perf matters (this repo deliberately scans everything for redesign-proofing); omit the throw-message-as-routing-channel only if your scheduler lacks a typed error lane. Extends visit-personalize-delegate's "cheap DOM probe" with the exact oracle + the found-href-becomes-the-send-url twist. Coverage caveat: source-grounded probes only; zero upstream tests.
