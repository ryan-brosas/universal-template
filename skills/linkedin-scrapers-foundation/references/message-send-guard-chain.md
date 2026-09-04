<!-- capsule-v2 -->
# Message-send guard chain — how do I send a LinkedIn chat message without duplicating myself or talking after the prospect replied?

**Source:** linvo-scraper MIT `main@cfbe911`→`cfbe910`; Codebase Memory `linvo-scraper`. **Question:** before typing into a conversation, which guards run, in what order, and how does the send get verified without any API?

## LinkedinMessageService.process — scrape history → 3-guard gate → contenteditable insert → count-delta verify
**Path/Symbol:** `lib/linkedin/linkedin.message.service.ts:LinkedinMessageService.process` (:54–216); `findInChat` (:40–52); `getMessagesList` (:218–287).
**Signature:** `async process(page: Page, cdp: CDPSession, data: {name; info?; contact?; message; url?; IgnoreProspectMessages: 0|1|2; image?}) -> {info, messages: {name, time, values}, name[]}`.
**Data Shape:** `IgnoreProspectMessages` is the guard policy enum: `0` = send regardless, `1` = require NO prospect message yet (first-touch), `2` = require prospect HAS replied (reply-mode). `getMessagesList` returns `{name, time: "YYYY-MM-DD HH:mm:ss" UTC, values: [{name, link, from:"Prospect"|"Me", message, sentiment}]}`.

### Decisive source
```ts
// GUARD 1+2 — reply-state and duplicate gates, evaluated over SCRAPED history
const onlyMyMessages = list.values.filter((f) => f.from === "Me");
const messageRanking =
  onlyMyMessages.length === 0 ? 0 :
  findBestMatch(message, onlyMyMessages.map((f) => f.message)).bestMatch.rating;

if (!( (IgnoreProspectMessages === 2 && list.values.some(f => f.from === "Prospect")) ||
       (IgnoreProspectMessages === 1 && !list.values.some(f => f.from === "Prospect")) ||
        IgnoreProspectMessages === 0 )) {
  throw new LinkedinErrors("Prospect Already Replied");
}
if (onlyMyMessages.some((f) => f.message.indexOf(message) > -1) ||
    messageRanking > 0.9) {
  throw new LinkedinErrors("Duplicate Message Avoided");
}

// TYPING — triple-click select + execCommand insert (contenteditable-safe)
await this.moveAndClick(page, '[contenteditable="true"]', undefined, 3);  // 3 = click count
await page.evaluate((wText) => {
  document.execCommand("selectAll", false, undefined);
  document.execCommand("insertText", false, wText);
}, message);

// SEND — two UI dialects behind ONE probe selector
await page.waitForFunction(() =>
  document.querySelector('.msg-form__send-button:not(:disabled), .msg-form__hint-text'));
if (type === "button") await this.moveAndClick(page,
  ".msg-form__send-button:not(:disabled), .msg-form__hint-text");
else                    await page.keyboard.press("Enter");

// VERIFY — message count MUST change, or the send silently failed
const totalBefore = await page.evaluate(() =>
  document.querySelectorAll(".msg-s-message-list__event").length);
await page.waitForFunction((before) =>
  document.querySelectorAll(".msg-s-message-list__event").length !== before,
  {}, totalBefore);
```
History scraper (`getMessagesList`) attributes each `.msg-s-message-list__event` group by comparing its profile-link text to the thread title (`from: top === theName ? "Prospect" : "Me"`), concatenates `[data-event-urn] p` fragments per group, and scores each message with the `sentiment` analyzer. Chat discovery when no url: search-box fallback ladder — if the name isn't in the visible h3 list, type into `input[name="searchTerm"]` + Enter, wait for the name to appear, re-resolve the `li[id]`, click it via `#${id} a`.
**Flow:** gotoUrl(url | /messaging/) → waitForLoader → optional search-chat discovery → wait contenteditable → getMessagesList (10s name-change timeout returns empty `{values: []}` sentinel on failure) → guards 1+2 → triple-click + selectAll/insertText → send-button-vs-hint-text dialect dispatch → Enter fallback → count-delta verification → return full updated transcript.
**Invariant:** every send is VERIFIED by DOM delta — never assume the click worked; duplicate detection must be fuzzy (`string-similarity` >0.9), not exact-match, because templating whitespace differs between runs; guards read the SCRAPED transcript, not local state, so they survive process restarts. Typing uses `execCommand("insertText")` because React-controlled contenteditable fields drop synthetic keyboard events' composition state.
**Probe:** no upstream tests (stub only) — caveat recorded; boundary verified by whole-file read at HEAD; graph anchor `LinkedinMessageService.process` resolves :54–216 exactly (top BM25 hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "LinkedinMessageService process Duplicate Message Avoided IgnoreProspectMessages", limit: 5 });
// resolves LinkedinMessageService.process :54–216
```

## Verdict
Adopt the guard chain (policy-gated reply check → fuzzy self-duplicate check → typed insert → count-delta verify) as the canonical unattended-messaging contract; adapt sentiment scoring and the 5000/10000ms timer lattice to host latency budgets; omit the hardcoded English-only search flow if targeting multilingual accounts (search relies on typed name matching h3 innerText). Contrast: Auto_job_applier's form-question-answering answers structured forms with validators; this guards free-text DMs against social errors (double-send, ghosting-after-reply) — different risk model, same "verify the DOM changed" discipline.
