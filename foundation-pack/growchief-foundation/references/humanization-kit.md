<!-- capsule-v2 -->
# Humanization kit — what makes clicks/typing human-like, and which parts are actually live vs dead code?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** a porter reading the files sees a rich typo engine and bezier cursor — which humanization is REAL at this pin, and what invariants must a reimplementation keep?

## Ghost-cursor paths + scrollend races are live; TypingTool.write() bypasses the typo engine
**Path/Symbol:** `shared/server/bots/bot.cursor.ts:createCursor` (:26-321); `shared/server/bots/typing.tool.ts:TypingTool` (engine :48-212, `write` :213-221); `shared/both/utils/timer.ts`.
**Signature:** `click(element: string|Locator, spreadOverride?, clientBoundingBox?)`; `type(text, options?) → writer.write(page, text, options)`.
**Data Shape:** `lastKnownLocation = {x,y}` module-level-per-cursor state threaded through every move; ghost-cursor `path(from, to, {moveSpeed, spreadOverride})` returns a waypoint list.

### Decisive source
```ts
// LIVE: every click walks a bezier path from the LAST position, then clicks the final waypoint
const route = path(lastKnownLocation, middleOfElement, { moveSpeed: 50, spreadOverride });
for (const step of route) await page.mouse.move(step.x, step.y);
await timer(100);
await page.mouse.click(route[route.length - 1].x, route[route.length - 1].y);
lastKnownLocation.x = route[route.length - 1].x;   // memory across actions
// 3-attempt retry wrapper around EVERY interaction: for (const a of [1,2,3]) { try {...} catch {} }
```
```ts
// DEAD: _getTypingFlow/_getCharacterCloseTo build typo+backspace streams with
// keyboard-neighborhood logic... but write() never calls them:
async write(page, text, options = {}) {
  return page.keyboard.type(text, { delay: 60 });   // plain constant-delay typing
}
```

**Flow:** bounding box resolution (locator vs selector vs client-side querySelector when `clientBoundingBox`) → center computed → path walked → settle timer → click. `scrollToElement` injects a `scrollend`-once listener racing a 3000ms setTimeout inside page.evaluate; `waitForCookie` polls `context.cookies()` for a named cookie up to 360s (login flows wait for session cookies); `scrollUntilElementIsVisible` wheels 50px/2s loop until `document.querySelector` finds the node.
**Invariant:** the lastKnownLocation handoff is what makes consecutive moves continuous (a fresh path from origin would look robotic); the triple-retry wrapper means a thrown interaction error is swallowed twice before propagating as "no action" — callers must treat silent no-op as a possible outcome. XProvider passes explicit HumanTypingOptions that set `chanceToKeepATypoInPercent:100, typoChanceInPercent:0` — options that only matter if write() used the flow engine, further evidence of the bypass.
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'page.keyboard.type' shared/server/bots/typing.tool.ts` → :218; `grep -n '_getTypingFlow' shared/server/bots/typing.tool.ts` → definition :150 only (zero call sites); `grep -n 'lastKnownLocation' shared/server/bots/bot.cursor.ts` → :39/:102/:115/:144/:153.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "createCursor TypingTool scrollToElement waitForCookie", limit: 10 });
```

## Verdict
Adopt: continuous-position bezier movement + settle timers + bounded-retry interaction wrapper + cookie-poll login barrier. Adapt the driver API. OMIT copying the dead typo engine unless you also wire it (reimplement from behavior description, not verbatim — AGPL).
