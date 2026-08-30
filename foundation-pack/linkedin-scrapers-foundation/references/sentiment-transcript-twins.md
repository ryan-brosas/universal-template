<!-- capsule-v2 -->
# Sentiment transcript twins — how do I turn a message-list DOM into per-speaker transcript rows with sentiment, without the merge bug one twin ships?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what is the correct reduce over `.msg-s-message-list__event` elements that segments a chat into speaker rows — and which of the repo's two implementations must be ported?

## Two implementations of ONE speaker-segmentation reduce (port the guarded-append twin)
**Path/Symbol:** `lib/linkedin/linkedin.messages.from.chat.ts:LinkedinMessagesFromChat.getMessagesList` values reduce (:98–140) VS `lib/linkedin/linkedin.message.service.ts:LinkedinMessageService.getMessagesList` (:218–287); both score via module singleton `const analyzer = new Sentiment()` (`sentiment` npm package, AFINN).
**Signature:** reduce over `document.querySelectorAll(".msg-s-message-list__event")` → rows `{name, link, time, from: "Prospect"|"Me", message}` → `.map(p => ({...p, sentiment: analyzer.analyze(p.message).score}))`.
**Data Shape:** header event (has profile-link element) OPENS a row; body event (`[data-event-urn] p`) EXTENDS the last row; speaker attribution = `top === theName ? "Prospect" : "Me"` where `theName` is the thread owner scraped from the topcard.

### Decisive source
```ts
// TWIN A (messages.from.chat :122–129) — REPLACE, unguarded: continuation
// events OVERWRITE earlier segments; a header-less event makes
// (" " + undefined).trim() === "undefined" a literal message string.
const message = current.querySelector("[data-event-urn] p")?.textContent?.trim();
all[all.length - 1] = { ...all[all.length - 1], message: (" " + message).trim() };

// TWIN B (message.service :271–277) — APPEND under a guard: the fixed kernel.
const message = current.querySelector("[data-event-urn] p")?.textContent?.trim();
if (message) {
  all[all.length - 1].message += " " + message;
  all[all.length - 1].message = all[all.length - 1].message.trim();
}
```

**Flow:** switch gate passes (see conversation-switch-gate-walk) → single in-page evaluate reduces all events left-to-right → header opens row, body appends text → out-of-page map scores each surviving message's sentiment → filter to rows with message+name (twin A) / no post-filter needed (twin B guards at insert).
**Invariant:** a row is opened ONLY by a profile-link header event and extended by every following header-less event until the next header — speaker segmentation is derived from DOM grouping, never from names inside text. Porters must take twin B's semantics: append-with-guard preserves multi-segment turns and cannot fabricate `"undefined"` strings.
**Divergence table (same kernel, four real differences):** failure value — twin A returns bare `undefined` (@ts-ignore), twin B a typed `{time:"none", name:"none", values:[]}`; read timestamp — twin A scrapes DOM `<time>` containing ":", twin B stamps `moment().utc().format("YYYY-MM-DD HH:mm:ss")`; selector era — twin B adds `.msg-s-message-group__name` to the header probe; merge — replace vs guarded append (above). Both attribute directionally by comparing the header name to the THREAD OWNER's name, so "Me"/"Prospect" survives avatar-only group headers.

**Probe:** no upstream tests at pin — recorded BLOCK; deterministic anchors executed instead: `grep -n 'all\[all.length - 1\].message +=' lib/linkedin/linkedin.message.service.ts` pins :275 (guarded append); `grep -n '(" " + message).trim()' lib/linkedin/linkedin.messages.from.chat.ts` pins :128 (replace trap); `grep -n 'analyzer.analyze' lib/linkedin/linkedin.message.service.ts lib/linkedin/linkedin.messages.from.chat.ts` pins :284 and :137.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "getMessagesList sentiment analyzer msg-s-message-list__event", limit: 8 });
```

## Verdict
Adopt twin B (guarded append + typed empty failure + UTC stamp) as the canonical transcript reducer and the header-opens/body-extends segmentation rule; adapt the header-selector list per DOM era and swap `sentiment`'s AFINN scores for your language (rows carry `language` from i18nLocale meta in the walk caller — AFINN is English-only, a silent mis-score for other locales); omit twin A's unguarded spread-replace except as a documented regression test fixture. Coverage caveat: probes are source-grounded; repo ships zero upstream tests.
