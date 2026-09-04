<!-- capsule-v2 -->
# Humanization & scroll discipline — how do I move and scroll a browser so lazy-load fires without looking robotic?

**Source:** linvo-scraper MIT (`autoScroll.ts` :1–20 LIVE; `show.mouse.ts:installMouseHelper` :1–84; `pagesTask` mouse-wheel ladder :159–180 and `scrollTo` retry :199–220 — **DEAD-AT-PIN cfbe910: both sit in sales.page.service's unreachable post-return tail, see post-return-stranded-dom-walk**); joeyism-linkedin-scraper GPL-3 (`scroll_to_bottom` :184–205, `click_see_more_buttons` :213–242); LinkedIn-Easy-Apply-Bot Apache-2.0 (`load_page` stepped scroll :655–667); EasyApplyJobsBot CC-BY-NC (random.uniform pacing). Codebase Memory projects of the same names. **Question:** which scroll/mouse patterns reliably trigger LinkedIn's virtualized lists while keeping timing human-variate?

## Four scroll disciplines + visible cursor
**Path/Symbol:** linvo `helpers/autoScroll.ts:autoScroll` (LIVE); linvo `pagesTask` wheel loop (:159–165) + residual-wheel (:168–178) + bounded-retry `scrollTo` (:199–220) — **unreachable at pin (post-return tail; pattern kept as design, not behavior)**; joeyism `core/utils.py:scroll_to_bottom` (:193–205); contrast LinkedIn-Easy-Apply-Bot `load_page` (:656–664). The LIVE linvo element-scrolled primitive at pin is `moveMouseAndScroll` (mouse-glide-wheel-hover).
**Signature:** `autoScroll(page)` — in-page setInterval(100px/150ms) until scrollTop stops changing; `scroll_to_bottom(page, pause_time=1.0, max_scrolls=10)` — height-diff loop; linvo `scrollTo(page, scrollName, time=0)` — recursion capped at 5 attempts.
**Data Shape:** termination signal = unchanged `document.documentElement.scrollTop` (linvo/joeyism) or unchanged `body.scrollHeight` (joeyism).

### Decisive source
```typescript
// linvo autoScroll: self-terminating in-page interval (no round-trips per step)
const interval = setInterval(() => {
    window.scrollBy(0, 100);
    if (document.documentElement.scrollTop !== scrollTop) { scrollTop = …; return false; }
    clearInterval(interval); resolve();      // stopped moving ⇒ bottom reached
}, 150);
// pagesTask human wheel: discrete mouse events with sleeps — NOT window.scrollTo
// (DEAD-AT-PIN in linvo: stranded below the response-plane return; keep the
//  discipline, verify reachability before citing as behavior)
for (let i = 1; i <= 7; i++) { await page.mouse.wheel({ deltaY: 400 }); await timer(2000); }
```
```python
# joeyism: pause between jumps so lazy content mounts before the next jump
previous_height = await page.evaluate('document.body.scrollHeight')
await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
await asyncio.sleep(pause_time)
new_height = await page.evaluate('document.body.scrollHeight')
if new_height == previous_height: break
# LinkedIn-Easy-Apply-Bot: fixed-step ladder for inner scroll containers
for i in range(300, 3000, 100): browser.execute_script("arguments[0].scrollTo(0,{})".format(i), el)
```

**Flow:** pick discipline by surface — full page → height-diff loop; virtualized container → stepped inner-element scroll (300→3000 by 100); Sales Nav card wall → real `mouse.wheel` bursts with 2 s settles (generates genuine wheel events some listeners require; in linvo at pin this burst lives in the stranded legacy plane, while the LIVE per-target variant is `moveMouseAndScroll`'s rect-derived wheel); per-card visibility → linvo's bounded recursive scrollTo on `[data-scroll-into-view]` (dead-at-pin design). `installMouseHelper` overlays a DOM cursor mirroring mousemove/buttons for debugging headless runs.
**Invariant:** every variant carries an explicit termination check (position or height unchanged) AND a bound (max_scrolls / recursion cap / range end) — unbounded "scroll until done" hangs on feeds that stream forever. Timing jitter comes from `time.sleep(random.uniform(...))` between actions (EasyApplyJobsBot pattern), never fixed delays.
**Probe:** joeyism pins lifecycle only (`tests/test_browser.py::test_browser_manager_headless_mode`); scroll helpers have no direct tests — coverage caveat recorded; all excerpts read at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linvo-scraper", query: "autoScroll", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "scroll_to_bottom", limit: 5 });
```

## Verdict
Adopt terminated+bounded scrolling with human-jittered pauses and container-scoped variants; adapt step sizes/settle times to host bandwidth; omit the pyautogui desktop wiggle (`avoid_lock`) and hard-coded 4000px ladders. Caveat: no upstream tests pin scroll behavior. Pin correction (2026-08-25, linvo pass 2): the linvo wheel-burst/scrollTo instance citations are unreachable code at `cfbe910` — treat them as pattern provenance only; live linvo evidence for element-scoped wheel+hover is mouse-glide-wheel-hover.
