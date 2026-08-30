<!-- capsule-v2 -->
# Chat scroll choreography — how does an auto-scrolling log stay pinned to the bottom without fighting a user reading history?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When porting the overlay's message feed, which scroll mechanisms run (per-append timer, post-mount burst, permanent poll), what does each fix, and what leaks if you keep only one?

## Three cooperating scroll layers: 100ms append-timer, 5×1s layout burst, forever-poll with stickiness test
**Path/Symbol:** `core/utils/ui/injectOverlay.js:addMessage` tail (:789-791), `setupScrollCheck` (:794-824), `maintainScroll` (:892-902) + its `setInterval` registration (:578).
**Signature:** `setupScrollCheck()` — self-cancelling; `maintainScroll()` — registered once per expansion via `setInterval(maintainScroll, 100)`; per-message `setTimeout(() => { chatBox.scrollTop = chatBox.scrollHeight; }, 100)`.
**Data Shape:** operates on `#tawebagent-chat-box` (`overflow-y: auto`, flex column); no state beyond the interval handles.

### Decisive source
```javascript
// :892-902 — the ONLY long-lived mechanism; sticky-bottom predicate
function maintainScroll() {
  const chatBox = document.getElementById("tawebagent-chat-box");
  if (!chatBox) return;
  const shouldScroll =
    chatBox.scrollHeight - chatBox.clientHeight <= chatBox.scrollTop + 1;
  if (shouldScroll) {
    chatBox.scrollTop = chatBox.scrollHeight;
  }
}
```
```javascript
// :799-806, :818-823 — display toggle forces reflow so scrollHeight is fresh
function refreshScroll() {
  chatBox.style.display = "none";
  chatBox.offsetHeight;            // Force reflow
  chatBox.style.display = "flex";
  const lastMessage = chatBox.lastElementChild;
  if (lastMessage) lastMessage.scrollIntoView({ behavior: "auto", block: "end" });
}
let checks = 0;
const interval = setInterval(() => { refreshScroll(); checks++;
  if (checks >= 5) clearInterval(interval); }, 1000);
```

**Flow:** every appended message schedules ONE +100ms bottom-pin (covers the common case); expanding the overlay runs `setupScrollCheck()` = immediate +100ms refresh then a 5-check ×1s burst of display-none→reflow→flex + `scrollIntoView` (defeats stale layout metrics right after DOM build and font/image settle); from then on a PERMANENT 100ms `maintainScroll` interval re-pins only while the user is already at bottom (within a 1px tolerance).
**Invariant:** (1) The stickiness predicate is what preserves manual scroll-up: `scrollHeight − clientHeight ≤ scrollTop + 1` must be true for auto-scroll to fire — replace it with unconditional pinning and users can never read history while steps stream. (2) The ref low trick (`element.offsetHeight` read between display writes) exists because freshly-inserted flex children report stale scrollHeight synchronously; deleting it makes the burst useless. (3) The 100ms interval is NEVER cleared on collapse — each expansion registers another copy, so long sessions accumulate timers (bounded work when collapsed since getElementById returns null, but porters should store the handle and clearInterval on removeOverlay).

**Probe:** `cd /mnt/hdd/utopia/inspo/TheAgenticBrowser && grep -n 'setInterval(maintainScroll' core/utils/ui/injectOverlay.js` → `578`; `grep -c 'checks >= 5' core/utils/ui/injectOverlay.js` → `1` (:822); `grep -c 'chatBox.scrollTop + 1' core/utils/ui/injectOverlay.js` → `1` (:897). No upstream tests; deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "maintainScroll setupScrollCheck", limit: 4 });
// rank-1/2: injectOverlay.maintainScroll 892-902 + setupScrollCheck 794-824
```

## Verdict
Adopt the three-layer split (per-append pin, short post-mount burst, sticky-bottom poll) — it is the minimal complete set for a streaming chat feed. Adapt intervals to your render cadence (a ResizeObserver/MutationObserver can replace all three, but keep the stickiness predicate). Omit nothing behavioral; do fix the un-cleared interval leak by storing the timer handle.
