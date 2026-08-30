<!-- capsule-v2 -->
# Active-element history — how does RestoreFocus know where focus WAS before the Dialog opened, across unmounts?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** Which events feed the global history ring, what filtering applies, and how do consumers snapshot it?

## history / active-element-history
**Path/Symbol:** `packages/@headlessui-react/src/utils/active-element-history.ts:5-40`; consumer `components/focus-trap/focus-trap.tsx:251-278` (`useRestoreElement`).
**Signature:** `export let history: (HTMLOrSVGElement & Element)[]` (module singleton); listeners registered once on document-ready for click/mousedown/focus at BOTH window and body level, all capture.
**Data Shape:** most-recent-FIRST array, capped at 10 entries, filtered to connected nodes on every push.

### Decisive source
```ts
export let history: (HTMLOrSVGElement & Element)[] = []
function handle(e: Event) {
  if (!DOM.isHTMLorSVGElement(e.target)) return
  if (e.target === document.body) return          // body focus is noise
  if (history[0] === e.target) return             // dedupe consecutive same-target
  // closest FOCUSABLE ancestor — clicking a <span> inside a button records the BUTTON:
  focusableElement = focusableElement.closest(focusableSelector)
  history.unshift(focusableElement ?? e.target)
  history = history.filter((x) => x != null && x.isConnected)   // drop detached nodes
  history.splice(10)                              // keep the 10 most recent
}
onDocumentReady(() => { window.addEventListener('click'|'mousedown'|'focus', handle, true)
                       document.body.addEventListener(same...) })
// FocusTrap consumer:
let localHistory = useRef(history.slice())        // SNAPSHOT at enable time
if (oldEnabled === false && newEnabled === true) localHistory.current = history.slice()
return useEvent(() => localHistory.current.find((x) => x != null && x.isConnected) ?? null)
```

**Flow:** every pointer/focus interaction unshifts the resolved focusable → stale entries fall out via isConnected filter + 10 cap → when a FocusTrap enables it COPIES the current history; on disable/unmount restore replays the copy's first still-connected entry. Disabling clears the LOCAL copy in a microTask so concurrent readers can finish first.
**Invariant:** recording is capture-phase at two levels (window catches iframe-adjacent and shadow events; body catches cases window misses); the snapshot-at-enable design means clicks that happen WHILE the dialog is open never poison the restore target.
**Probe:** deterministic checks executed: dedupe guard, closest-focusable resolution, connected filter. Direct coverage: focus-trap.test.tsx restore suites + dialog tests asserting focus returns to the trigger button on close.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "active-element-history", name_pattern: "^history$", limit: 5 });
```

## Verdict
Adopt the event-fed ring + snapshot-on-enable pattern verbatim; adapt cap size freely; omit the body-level duplicate listeners only after verifying your host's focus-event propagation. This is the missing piece that makes modal close→refocus work even when the trigger re-rendered.
