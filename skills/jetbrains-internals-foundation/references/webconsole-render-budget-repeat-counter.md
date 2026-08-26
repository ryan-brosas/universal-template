<!-- capsule-v2 -->
# WebConsole render budget & repeat counter - how does an append-only DOM log stay bounded without losing history?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How do you cap a live log view's DOM size while keeping every evicted line recoverable?

## webConsole render budget
**Path/Symbol:** `plugins/javascript-debugger/webConsole/WebConsole.js:_addMessage` (:468-490), `hideMessages` (:527-549), `setMaxRenderedCount` (:194-196, default 2000 at :143), `MessagesHolder` (:601-621), `increaseLastMessageRepeatCount` (:260-269), `RepeatCounter` (:623-635).
**Signature:** `_addMessage(message)` → optional `hideMessages()`; `hideMessages()` evicts exactly `renderedMessages - maxRenderedCount` in one run; `MessagesHolder.expand()` re-inserts all saved messages before the holder node and removes it.
**Data Shape:** `renderedMessages` counter; eviction budget `maxRenderedCount` (host-tunable via setMaxRenderedCount — the JVM page loader calls it); holder = `{root: div.saved-messages("Show previous logs"), savedMessages: Message[]}` with back-reference planted as `this.root.class = this`.

### Decisive source
```js
// groups counted as one rendered message
if (this.rootGroup === this.currentGroup) this.renderedMessages++;
if (this.renderedMessages > this.maxRenderedCount) this.hideMessages();

hideMessages() {
  if (this.renderedMessages <= this.maxRenderedCount) return;
  const singleRun = this.renderedMessages - this.maxRenderedCount;
  let messagesHolder;
  if (this.messageContainer.firstChild.class instanceof MessagesHolder
      && this.messageContainer.firstChild.class.savedMessages.length < this.maxRenderedCount)
    messagesHolder = this.messageContainer.firstChild.class;      // reuse while capacity lasts
  else { messagesHolder = new MessagesHolder();
         this.messageContainer.insertBefore(messagesHolder.root, this.messageContainer.firstChild); }
  let currentMessage = this.messageContainer.firstChild.nextSibling;
  ... // remove oldest `singleRun` roots, push into holder.savedMessages
}
expand() { // on click: re-insert every saved message BEFORE the anchor, then remove the holder
  for (let message of this.savedMessages) parent.insertBefore(message, anchor);
  this.savedMessages = []; this.root.remove();
}
```

**Flow:** Every root-level message increments the counter (nested group children are free — a collapsed group is one rendered unit). Overflow moves the OLDEST messages under a "Show previous logs" node pinned at the TOP; clicking it splices them back in original order. The JVM drives dedup separately: when the same message repeats it calls `increaseLastMessageRepeatCount()` — the first repeat lazily creates a `RepeatCounter` labeled **2** (`this.count = 2`, WebConsole.js:626) inserted `beforebegin` the message container and adds class `repeated-message`; later repeats just bump the label.
**Invariant:** eviction never destroys data (it relocates into a re-expandable holder); per-run eviction equals exactly the overflow amount; a reused holder must still have headroom (< maxRenderedCount saved) or a fresh one is created; repeat collapsing is host-driven — the page never diffs messages itself.
**Probe:** DOM-bound → byte-exact content pins executed: `this.count = 2;` → :626; `insertBefore(message, anchor)` → 1 match (:615); budget default `this.maxRenderedCount = 2000` read at :143 during whole-file read.
**Coverage caveat:** coverage no_recorded_issue @ gen 2026-08-24T13:57:05Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "rendered messages holder hide", limit: 5 });
```

## Verdict
Adopt count-based eviction into a re-expandable holder whenever a streaming view must stay light but lossless. Adapt the counting rule to your grouping semantics (count top-level units, not leaves). Keep lazy first-repeat=2 counters instead of pre-allocating badges. Omit host-driven repeat detection only if you can diff cheaply client-side.
