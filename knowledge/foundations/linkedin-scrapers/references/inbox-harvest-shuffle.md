<!-- capsule-v2 -->
# Inbox harvest shuffle — how do I scrape an entire LinkedIn messaging inbox while looking like a human browsing it?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** how do I enumerate every conversation without the visit ORDER betraying automation, and how many rows can I touch per pass?

## LinkedinMessagesFromChat.continueGetAllMessagesFromChat — visible-budget → filter ads → SHUFFLE → recurse
**Path/Symbol:** `lib/linkedin/linkedin.messages.from.chat.ts:LinkedinMessagesFromChat.continueGetAllMessagesFromChat` (:199–240); `totalVisibleElement` (:185–197); `nextPerson` (:148–183); `getMessagesList` (:23–146).
**Signature:** `async continueGetAllMessagesFromChat(page: Page) -> Array<{id, time, name, link, list: Message[], img, language}>`; `totalVisibleElement(page) -> number`; `nextPerson(page, idList: string[], name, language)` recursive.
**Data Shape:** conversation rows = `.msg-conversations-container__conversations-list > li:not(:empty)`; eligible ids must contain `ember`; ad rows detected by innerText needles `InMail | LinkedIn Offer | Sponsored`. Per-chat payload carries `language` from `meta[name="i18nLocale"]` split on `_`.

### Decisive source
```ts
// BUDGET — count how many list rows are actually on-screen (viewport math)
const visibility = await this.totalVisibleElement(page);
//   = floor(containerHeight / firstNonEmptyRowHeight)
const all = shuffle(
  (await page.evaluate((vis) => {
    return Array.from(document.querySelectorAll(
      ".msg-conversations-container__conversations-list > li:not(:empty):not(.msg-conversation-card--occluded)"
    )).map((f) => ({
      id: f.getAttribute("id"),
      filter: f.innerHTML.indexOf("InMail") > -1 ||
              f.innerHTML.indexOf("LinkedIn Offer") > -1 ||
              f.innerHTML.indexOf("Sponsored") > -1,
    }))
      .filter((f) => (f.id || "").indexOf("ember") > -1)
      .slice(0, vis);            // <-- HARD CAP: only viewport-visible count
  }, visibility))
    .filter((f) => !f.filter)
    .map((p) => p.id)
);
// RECURSIVE WALK — pop one id, open chat, harvest, continue with REST of ids
return (await this.nextPerson(page, all as any, "", language!))
  .filter((f: any) => f?.name && f?.list.length);
```
`nextPerson` shifts one id, clicks `#${id} .msg-conversation-card__body-row`, waits 2000ms, scrapes via `getMessagesList`, and recurses on the remaining idList — threading the LAST scraped name through as the `lastName` change-detector so each chat transition waits for the thread title to differ (10s timeout ⇒ chat skipped via undefined sentinel). Message attribution twin of message.service's scraper but adds per-message `time` (first `<time>` containing `:`) and drops empty rows (`filter(p?.message && p?.name)`).
**Flow:** wait non-empty list → measure visible row height ratio → collect ember ids minus occluded/ads → cap at visible count → **shuffle** → recursive click-and-harvest → keep only chats with name + messages.
**Invariant:** order randomization is the point — a sequential top-to-bottom sweep of an inbox is a bot signature; the visible-count budget keeps each pass to what a human could see in one screenful (unseen rows require a scroll/re-entry, which naturally re-shuffles). The `lastName` threading is what makes the 10s timeout a SKIP signal rather than a crash.
**Probe:** no upstream tests (stub only) — caveat recorded; boundary verified by whole-file read at HEAD; graph anchors `continueGetAllMessagesFromChat` :199–240 and `totalVisibleElement` :185–197 resolve uniquely.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "continueGetAllMessagesFromChat totalVisibleElement shuffle conversations-list", limit: 5 });
```

## Verdict
Adopt visible-budget + shuffle-before-walk as the anti-detection enumeration pattern (pairs with humanization-scroll for feed surfaces); adapt the InMail/Offer/Sponsored filter needles and the ember-id validity check to current markup; omit `console.log(a)` debug residue (:142). Contrast: voyager-dual-collection-sort randomizes/sorts FEED collection server-side via two API collections; this shuffles CLIENT-side DOM walking when no API is available — same goal (defeat order-based bot detection), opposite layer.
