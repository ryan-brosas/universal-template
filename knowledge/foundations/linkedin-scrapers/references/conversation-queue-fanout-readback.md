<!-- capsule-v2 -->
# Conversation queue fan-out + read-back — how do I queue several messages into several threads and RETURN trustworthy state afterwards?

**Source:** linvo-scraper ISC `main@cfbe91080c73`; Codebase Memory `linvo-scraper`. **Question:** when one action must write MANY messages across MANY conversation links, what resets SPA state between threads, what proves each send, and whose answer does the action return?

## LinkedinMessagesService.process — batch writer that returns the READER's result
**Path/Symbol:** `lib/linkedin/linkedin.messages.service.ts:LinkedinMessagesService.process` (:24–81; per-message verify :45–70; terminal delegation :78–80). Module-scope singleton: `const messagesFromChat = new LinkedinMessagesFromChat()` (:9).
**Signature:** `process(page, cdp, data: { messages: Array<{ id, name, messages: string[], link }> }) -> whatever continueGetAllMessagesFromChat(page) returns`.
**Data Shape:** input is a queue of conversations, each carrying an ORDERED array of message strings and its chat deep-link; output is the messaging READ path's fresh walk of /messaging/ — NOT a send receipt.

### Decisive source
```ts
for (const messages of data.messages) {
  await page.goto('about:blank');            // reset SPA state BEFORE the next thread
  gotoUrl(page, messages.link);              // unawaited, swallowed
  await this.waitForLoader(page);
  for (const message of messages.messages) {
    await timer(5000);
    await this.moveAndClick(page, '[contenteditable="true"]');
    await page.keyboard.type(message, { delay: 10 });
    await page.keyboard.press("Enter");      // newline inside the box — NOT send
    await timer(1000);
    await page.waitForFunction(() => document.querySelector(
      ".msg-form__send-button:not(:disabled), .msg-form__hint-text"));
    const totalBefore = await page.evaluate(() =>
      document.querySelectorAll(".msg-s-message-list__event").length);
    await this.moveAndClick(page, ".msg-form__send-button:not(:disabled), .msg-form__hint-text");
    await page.waitForFunction((before) =>
      document.querySelectorAll(".msg-s-message-list__event").length !== before, {}, totalBefore);
  }
}
await page.goto('https://www.linkedin.com/messaging/');
return messagesFromChat.continueGetAllMessagesFromChat(page);
```

**Flow:** per conversation: about:blank → loader-latched goto → per message: click composer → typed insert (10 ms/char) → Enter inserts newline → wait send-button enabled/hint → snapshot list length → click send → WAIT until `.msg-s-message-list__event` count differs from before. Inner try/catch isolates one message; outer isolates one conversation; both swallow. Terminal: goto /messaging/ and return the read-path walker's harvest.
**Invariant:** a send is "real" only when the message-list DOM count DELTAS — never trusted from the click resolving; writers NEVER certify their own writes: the return value comes from the separate read path (`continueGetAllMessagesFromChat`); about:blank between threads kills LinkedIn's composer state carry-over. Contrast: single-thread policy guards live in message-send-guard-chain (LinkedinMessageService); this is the multi-thread QUEUE around them.
**Probe:** no upstream tests (blocker). Deterministic anchors: about:blank-before-goto ordering + count-delta waitForFunction + terminal read-back delegation at HEAD — verification.md probe P4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "continueGetAllMessagesFromChat", limit: 5 });
```
Resolves `LinkedinMessagesFromChat.continueGetAllMessagesFromChat` :199–240 (the delegated read path).

## Verdict
Adopt the three-part contract: SPA reset per thread, count-delta send proof, reader-certified return. Adapt pacing timers to your throttle budget and route sends through message-send-guard-chain's reply-state/duplicate gates first. Omit the empty catch blocks in any host that needs per-item error reporting — but keep failure isolation per message so one bad thread cannot kill the queue.
