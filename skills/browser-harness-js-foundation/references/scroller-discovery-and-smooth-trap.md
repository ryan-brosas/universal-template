<!-- capsule-v2 -->
# scroller-discovery-and-smooth-trap — which scroll primitive works per surface, and why does smooth-scrolling eat coordinate clicks?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** When does wheel-vs-scrollIntoView-vs-scrollTop matter, and how do you find the container actually consuming wheel events?

## Three-level scroll ladder + scroller discovery
**Path/Symbol:** `skills/cdp/interaction-skills/scrolling.md` whole doc — ladder (:3–7), wheel (:9–24), scrollIntoView (:26–35), scrollTop (:37–48), which-container discovery (:50–69), Traps (:71–75).
**Signature:** wheel: `Input.dispatchMouseEvent({type:'mouseWheel', x, y, deltaX, deltaY})`; instant jump: `el.scrollIntoView({block:'center', behavior:'instant'})`; blunt: `el.scrollTop = el.scrollHeight`; discovery: walk `getComputedStyle` for `(overflowY === 'auto' || 'scroll') && el.scrollHeight > el.clientHeight`.
**Data Shape:** order-by-reliability: (1) wheel at a point — scrolls whichever element is under (x,y), the ONLY reliable scroll inside virtualized lists (`react-window`, TanStack Virtual) because unmounted rows make scrollIntoView no-op; (2) scrollIntoView with behavior:'instant' avoids animation round-trips; (3) scrollTop direct-set bypasses snap/animation for absolute offsets.

### Decisive source
```js
const s = getComputedStyle(el)
if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight)
  out.push({ tag: el.tagName, cls: el.className, h: el.clientHeight, scroll: el.scrollHeight })
```

**Flow:** ambiguous page → run discovery snippet to list real scrollers → pick coordinates OVER the consuming element (wheel over sticky header = nothing happens) → infinite-scroll sentinels needing momentum get SEVERAL smaller wheels in a loop, not one deltaY:300.
**Invariant:** CSS `scroll-behavior: smooth` makes wheel return instantly while the page keeps moving — the NEXT coordinate click lands mid-flight unless you wait (~400ms) or force behavior:'instant'. Layout shifts after dropdown/modal open invalidate cached rects.
**Probe:** `grep -cF 'mouseWheel' skills/cdp/interaction-skills/scrolling.md` → 3; `grep -cF "'instant'" <same>` → 3; `grep -cF 'el.scrollTop = el.scrollHeight' <same>` → 1; `grep -cF 'overflowY' <same>` → 1; `grep -cF 'momentum' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "scrollIntoView" (Module node resolves line-exact).

## Verdict
Adopt the ladder ordering + discovery snippet as portable doctrine. Adapt dwell times to observed site behavior. Omit nothing — this doc is minimal-correct already.
