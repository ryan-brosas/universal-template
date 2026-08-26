<!-- capsule-v2 -->
# Conversation switch-gate walk — how do I harvest N conversations one-by-one when every read depends on knowing the PREVIOUS thread?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** how does an agent walk a shuffled list of inbox threads and reliably detect that the click actually switched the conversation before parsing it?

## LinkedinMessagesFromChat — shift-consume recursion behind a name-inequality switch gate
**Path/Symbol:** `lib/linkedin/linkedin.messages.from.chat.ts:LinkedinMessagesFromChat.nextPerson` (:148–183) + `getMessagesList` switch gate (:34–53) + `totalVisibleElement` viewport budget (:185–197); orchestrator `continueGetAllMessagesFromChat` (:199–240).
**Signature:** `nextPerson(page: Page, idList: string[], name: string, language: string): Promise<any[]>`; `getMessagesList(page: Page, lastName: string)`; `totalVisibleElement(page): Promise<number>`.
**Data Shape:** idList = ember-ids of visible non-occluded, non-InMail/Offer/Sponsored `<li>` rows, sliced to `Math.floor(containerHeight / rowHeight)` and shuffled by the caller; each result row `{id, time, name, link, list: Message[], img, language}`; a failed thread contributes NO row (not an empty row).

### Decisive source
```ts
// THE SWITCH GATE: "the topcard no longer shows the person I just harvested"
await page.waitForFunction(
  (last) => last !== document?.querySelector(
    '[data-control-name="topcard"] h2, .msg-entity-lockup__entity-title-wrapper h2'
  )?.textContent?.trim(),
  { timeout: 10000 },
  lastName                       // <- the PREVIOUS thread's name rides the recursion
);
await page.waitForSelector(".msg-s-message-list__loader.hidden"); // history finished loading
} catch (err) { return; }        // timeout => undefined => row omitted, walk continues

const current = idList.shift();  // consume head
await this.moveAndClick(page, `#${current} .msg-conversation-card__body-row`);
const load = await this.getMessagesList(page, name);
return [
  ...(load?.id ? [{ id: load.id, time: load.time, name: load.name || "", link: load.link || "",
                    list: load.values, img: load.img || "", language }] : []),
  ...(await this.nextPerson(page, idList, load?.name || "", language)),
];
```

**Flow:** budget = floor(list height ÷ first row height) → collect visible ember rows → filter promo cards → shuffle (order randomization owned by `inbox-harvest-shuffle`) → recurse: click row → 2000ms settle → switch gate waits until topcard ≠ previous name → loader-hidden latch → parse transcript + identity → append row only if `load.id` truthy → recurse with `load?.name || ""` as the new discriminator → final `.filter(f => f?.name && f?.list.length)` drops husks.
**Invariant:** the discrimination argument is ALWAYS the previously harvested thread's name, never a constant — on the first call it is `""` so any real topcard passes; after a failed/timeout read the recursion still advances but carries `""`, so the next gate accepts whatever thread is open. Parsing never begins before BOTH the thread switched AND `.msg-s-message-list__loader.hidden` proves older history finished loading; a 10s gate timeout degrades to row-omission, never to a wrong-thread transcript.
**Probe:** no upstream test runner exists at this pin (scripts start/watch/build only) — recorded BLOCK; deterministic source anchors executed instead: `grep -n "last !==" lib/linkedin/linkedin.messages.from.chat.ts` pins :38 inside the waitForFunction; `grep -n "idList.shift()" …` pins :158; `grep -n "load?.name || \"\"" …` pins :181.
**Contrast trap (engagement service :27–40):** a `waitForFunction` returning a MAPPED ARRAY is truthy even when empty ⇒ single-pass no-op latch. The switch gate avoids this by returning a boolean comparison (`last !== topcard`). Porters: wait predicates must reduce to booleans, not collections.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "nextPerson continueGetAllMessagesFromChat totalVisibleElement", limit: 8 });
```

## Verdict
Adopt the previous-name threading as the universal "did my click land" gate for SPA panel navigation and shift-consume recursion with per-row degradation; adapt the selectors (dual-era topcard h2 pairs rot), the 10s gate timeout, and the viewport-budget arithmetic to your surface; omit the console.log(a) debug spill in getMessagesList (:142). Coverage caveat: source-grounded probes only, repo ships zero tests; the shuffle/budget ordering contract lives in inbox-harvest-shuffle, the write-side send guards in message-send-guard-chain.
