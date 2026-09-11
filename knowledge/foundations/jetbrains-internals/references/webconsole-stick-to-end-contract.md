<!-- capsule-v2 -->
# WebConsole stick-to-end contract - how does an embedded view negotiate autoscroll with its host process?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How should a streaming log view keep pinned to the bottom until the user deliberately scrolls away — and tell the host about it?

## webConsole stick-to-end
**Path/Symbol:** `plugins/javascript-debugger/webConsole/WebConsole.js:setStickToEnd` (:210-218), `_onScroll` (:223-231), `_onMouseDown` (:236-242), `_notifyStickToEndChange` (:247-249), `scrollDown` (:251-254); gap constant `scrollStickGapSize = 60` (:137); initial state `_stickToEnd = true` (:136).
**Signature:** `setStickToEnd(value)` (host-initiated), scroll/mousedown listeners (user-initiated), `_notifyStickToEndChange(state)` → `callJVM("updateStickToEnd", [state])` (page→host push, see webconsole-jsbridge-callback-registry).
**Data Shape:** one boolean + one 60px threshold; document.scrollingElement scrollTop/scrollHeight/innerHeight arithmetic.

### Decisive source
```js
setStickToEnd(value) {
  this._stickToEnd = value;          // synchronous write
  setTimeout(() => {
    this._stickToEnd = value;        // re-write AFTER pending scroll events drain
    if (value) this.scrollDown();
  }, 0);
}
_onScroll(event) {
  let bottom = document.scrollingElement.scrollHeight - window.innerHeight;
  let curY   = document.scrollingElement.scrollTop;
  let stick  = bottom - curY < this.scrollStickGapSize;   // within 60px of bottom?
  if (stick !== this._stickToEnd) { this._stickToEnd = stick;
    WebConsole._notifyStickToEndChange(stick); }
}
_onMouseDown(event) {  // a grab far above the bottom unsticks even without scrolling
  let clickY = document.scrollingElement.scrollTop + event.clientY;
  if (this._stickToEnd && document.scrollingElement.scrollHeight - clickY > this.scrollStickGapSize) {
    this._stickToEnd = false; WebConsole._notifyStickToEndChange(this._stickToEnd);
  }
}
```

**Flow:** The page is the authority on user intent: any scroll that leaves the 60px bottom band flips the flag and pushes it to the JVM (`updateStickToEnd`) so the host can stop tailing; a mousedown more than 60px above the bottom unsticks immediately. When the HOST wants to force sticking (e.g. "scroll to end" action or resume-tail), setStickToEnd writes the flag twice — once synchronously, again inside setTimeout(0) followed by scrollDown() — so the intent survives any scroll events already queued in this task queue.
**Invariant:** hysteresis band = 60px in BOTH directions (stick and unstick share the same gap); every user-driven flip is mirrored to the host; programmatic stick defers confirmation by one macrotask.
**Probe:** DOM-bound → byte-exact content pins executed: `grep -n "scrollStickGapSize = 60"` → :137; `callJVM("updateStickToEnd", [state])` → :248; `setTimeout(() => {` double-write → :212. Companion native-find surface in the same view-control family (`search.js:15`): `findNext` collapses selection to END then `self.find(text, caseSensitive, false, true)`; `findPrev` collapses to START with backward=true — direction encoded purely in where the selection collapses; `lastSearch` memo (:2) makes next/prev stateless calls. CEF's nonstandard `self.find()` is the whole implementation — no DOM scanning.
**Coverage caveat:** coverage no_recorded_issue ×4 cited paths @ gen 2026-08-24T13:57:05Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "stick to end scroll notify", limit: 5 });
```

## Verdict
Adopt the 60px-band + explicit page→host notification for ANY tailing log view embedded beside an owner process. Adapt the transport (JSBridge → postMessage/RPC). Keep the double-write/setTimeout(0) idiom whenever programmatic state must win over already-queued UI events; Omit mousedown handling only for read-only views without pointer grabbing.
