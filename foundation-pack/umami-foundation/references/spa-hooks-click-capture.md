<!-- capsule-v2 -->
# SPA navigation & event-delegated click tracking — how do you capture route changes and data-attribute events in any frontend framework?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are pushState/replaceState hooked without breaking the host app, and how do declarative click events fire before navigation?

## spa-hooks-click-capture
**Path/Symbol:** `src/tracker/index.ts:handlePush :339-353, handlePathChanges :355-374, handleClicks :383-419`.
**Signature:** `hook(history, 'pushState'|'replaceState', cb)` wraps the native method: `orig.apply(...)` THEN callback, returning the original result.
**Data Shape:** declarative events via attributes: `data-umami-event="Name"` plus `data-umami-event-<key>` payload attrs extracted by `/data-umami-event-([\w-_]+)/`.

### Decisive source
```ts
const onClick = (e: MouseEvent) => {
  const eventEl = (e.target as Element).closest(`[${eventNameAttribute}]`);
  if (!eventEl) return;
  if (eventEl.tagName === 'A' && (eventEl as HTMLAnchorElement).href) {
    const { href, target } = eventEl as HTMLAnchorElement;
    const external = target === '_blank' || e.ctrlKey || e.shiftKey || e.metaKey || (e.button && e.button === 1);
    if (!external) e.preventDefault();
    return trackElement(eventEl).finally(() => {
      if (!external) {
        (target === '_top' ? (top as WindowProxy).location : location).href = href;   // navigate AFTER send
      }
    });
  }
  return trackElement(eventEl);       // non-anchor: pure side-effect event
};
document.addEventListener('click', onClick, true);   // CAPTURE phase
```

**Flow:** capture-phase listener → closest() delegation (works for dynamically added DOM) → same-tab links defer navigation until the keepalive fetch is dispatched (`finally`) → history hooks fire pageviews with referrer = previous URL.
**Invariant:** `preventDefault` + manual navigation ONLY for non-modifier same-tab clicks — modifier/middle/new-tab clicks must never be intercepted. Capture phase matters: host apps may stopPropagation in bubble phase. The pushState wrapper must preserve `this`/args and the ORIGINAL return value or framework routers break.
**Probe:** structural pins: `grep -n "capture" src/tracker/index.ts | head -2` → :419 and readystate :651; `grep -n "eventRegex" src/tracker/index.ts` → :336.
**Probe:** `grep -cF "e.preventDefault()" src/tracker/index.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "handlePathChanges handleClicks pushState hook", limit: 10 });
```

## Verdict
Adopt capture-phase delegation + navigation-deferred-until-send for embeddable trackers; adapt attribute namespace; omit window.top handling if never framed.
