<!-- capsule-v2 -->
# Mouse glide wheel hover — what is the reusable interaction primitive that positions a ghost cursor, scrolls by an element's own geometry, and hovers before acting?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** how should one shared helper combine human-like cursor glide + real wheel scroll + hover so every action service gets identical pre-click behavior?

## LinkedinAbstractService.moveMouseAndScroll — rect-derived glide/wheel/hover primitive (8 call sites)
**Path/Symbol:** `lib/linkedin/linkedin.abstract.service.ts:LinkedinAbstractService.moveMouseAndScroll` (:116–160); inherited by every concrete service.
**Signature:** `moveMouseAndScroll(page: Page, selector: string, timeout?: number, disabledMouseMove?: boolean, offset = 0): Promise<void>`.
**Data Shape:** reads `{top, y, height}` from the element's `getBoundingClientRect` in-page; `offset` shifts both glide target and wheel distance (callers use `-700` to pull a target UP into mid-view before clicking it); GhostCursor arrives as `page.cursor` (ghost-cursor package attached elsewhere).

### Decisive source
```ts
await page.waitForSelector(selector, { visible: true, timeout });
const pos = await page.evaluate((elm) => {
  const { top, y, height } = document?.querySelector(elm)?.getBoundingClientRect();
  return { top, y, height };
}, selector);
try {                                   // HALF 1: glide to the element's BOTTOM edge
  await cur.moveTo({                    // at a RANDOM x — never the same path twice
    y: pos.y + pos.height + offset,
    x: randomIntFromInterval(300, 1000),
  });
  await page.mouse.wheel({ deltaY: pos.top + offset }); // wheel by ITS OWN rect
} catch (err) {}                        // each half swallows independently
await timer(300);
if (!disabledMouseMove) {
  try {                                 // HALF 2: hover the element itself
    await cur.move(selector, { moveDelay: 300, paddingPercentage: 30,
                               waitForSelector: 200 });
  } catch (err) {}
}
await timer(1000);
```

**Flow:** visible-wait → measure rect → glide cursor to bottom-edge+offset at random x → emit ONE real `mouse.wheel` whose deltaY equals the element's own `top+offset` → jittered 300ms pause → unless suppressed, hover with 30% padding and per-move delay → jittered 1000ms settle.
**Invariant:** the two halves fail independently and silently (each has its own try/catch), so a broken glide never blocks the hover and vice versa; scroll distance is DERIVED from the target element's own geometry (`pos.top + offset`), never a hardcoded constant, which keeps the same call correct at any viewport/scroll position; all pacing flows through `timer()` so ±1s jitter applies here too.
**Live vs dead callers at this pin (graph trace + source read):** LIVE — `connect.clickConnectButton`, `connect.connectMethod3`, `endorse.process`, `engagement.process` (the −700 pre-position pattern lives there). DEAD — `page.service.elements/pagesTask` and `sales.page.service.scrollTo/workOnResults` call sites sit inside those files' unreachable post-return tails (see post-return-stranded-dom-walk).
**Probe:** no upstream test runner exists at pin — recorded BLOCK; deterministic anchors executed instead: `grep -n "randomIntFromInterval(300, 1000)" lib/linkedin/linkedin.abstract.service.ts` pins :139; `grep -n "deltaY: pos.top + offset" …` pins :143; `grep -n "paddingPercentage: 30" …` pins :153.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "moveMouseAndScroll ghost cursor wheel", limit: 8 });
```

## Verdict
Adopt as the standard PRE-ACTION primitive whenever a click must look human AND land in view: measure-then-derive beats absolute coordinates; adapt the random-x window [300,1000], offset conventions, padding/delay constants, and swap ghost-cursor for your driver's synthetic mover; omit nothing silently — if you drop the hover half, pass `disabledMouseMove=true` explicitly like engagement's callers could. Complements ghost-cursor-click-ladder (which owns the CLICK degradation ladder this helper precedes) and humanization-scroll (which owns container-level scroll disciplines; its linvo instance citations are dead-at-pin, see post-return-stranded-dom-walk). Coverage caveat: source-grounded probes only.
