<!-- capsule-v2 -->
# Ghost-cursor click ladder — how do I click like a human (real cursor events) yet still survive when the human-like path fails?

**Source:** linvo-scraper MIT `main@cfbe910`; Codebase Memory `linvo-scraper`. **Question:** what is the fallback order that keeps ghost-cursor clicks reliable without reverting the whole app to raw DOM clicks?

## moveAndClick — container-offset math, ghost-cursor move, real mouse click, three-tier degradation
**Path/Symbol:** `lib/linkedin/linkedin.abstract.service.ts:LinkedinAbstractService.moveAndClick` (:367–430); cursor bootstrap `lib/helpers/load-cursor.ts:loadCursor` (:1–10); jitter clock `lib/helpers/timer.ts:timer`.
**Signature:** `async moveAndClick(page: Page, select: string | {container: string; selector: string}, timeout?: number, totalClicks?: number) -> ElementHandle | void`.
**Data Shape:** selector is a plain CSS string OR `{container, selector}` where only `container.offsetTop` is subtracted from viewport coordinates (for elements inside scrolled sub-containers); `totalClicks` maps to puppeteer's `clickCount` (double-click = 2).

### Decisive source
```ts
const offset = typeof select === "string" ? 0 :
  await page.evaluate((el) => document.querySelector(el)?.offsetTop || 0, select.container);
await page.waitForSelector(selector, { visible: true, timeout });
await timer(randomIntFromInterval(200, 444));          // pre-click human pause
const pos = await elm.boundingBox();
const cur = page.cursor as GhostCursor;                // installed once by loadCursor(page, headless)
try { await cur.moveTo({ x: pos.x + pos.width / 2,
                         y: pos.y - offset + pos.height / 2 }); }
catch { try { await cur.move(selector); } catch {} }   // tier 2: cursor's own finder
try { await page.mouse.click(pos.x + pos.width / 2,
                             pos.y - offset + pos.height / 2,
                             { clickCount: totalClicks }); }             // REAL event at coords
catch { try { await page.click(selector, { clickCount: totalClicks }); } catch {} } // tier 3: DOM click
```

**Flow:** wait visible → jittered pause → resolve position (minus container offset) → ghost-cursor glide → dispatch a genuine `mouse.click` at those coordinates → ONLY if the trusted-event path throws, degrade to `page.click`; if no element handle exists at all, last resort is an in-page `document.querySelector(elm).click()`. Every LinkedIn action service (connect/message/like/endorse/engagement) calls this instead of bare clicks — one chokepoint for "how clicking happens".
**Invariant:** the human-like path is tried FIRST and the synthetic path is the FALLBACK, never the reverse — flipping the order silently converts the whole bot into a detectable DOM-clicker; every degraded step is individually try-wrapped so one failed tier never aborts the action. Cursor is created ONCE per page (`page.cursor = await createCursor(page)`) and reused.
**Probe:** no upstream tests — caveat recorded; boundary verified by reading abstract.service.ts + all consumer services at HEAD; graph anchor `moveAndClick` resolves :367–430 exactly; fan-out to 12+ call sites in connect/message/engagement/like services.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "moveAndClick GhostCursor boundingBox", limit: 5 });
// resolves LinkedinAbstractService.moveAndClick :367–430
```

## Verdict
Adopt the ordered ladder (ghost-cursor glide → coordinate mouse click → DOM click fallback) with the single-cursor-per-page lifecycle and the container-offset variant; adapt jitter ranges and padding options; omit linvo's silent-swallow of ALL failures (a port should at least count degradations). Contrast: Auto_job_applier's selenium-click-finder-ladder solves locator tolerance in Selenium; linvo solves EVENT realism in Puppeteer with graceful degradation — they compose as locator layer under realism layer.
