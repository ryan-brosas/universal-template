<!-- capsule-v2 -->
# CDP terminal-use plane — how do I rasterize a terminal pane to PNG and synthesize mouse input through the browser, with a headless fallback?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do capture-pane --png and session mouse reuse a live viewer tab vs an ephemeral background tab, and when does each degrade to SGR/text paths?

## resolveTab → waitForRenderLanded → dispatch (or SGR fallback)
**Path/Symbol:** `packages/server/src/session-automation.ts:resolveTab` (54–83), `waitForRenderLanded` (91–110), `capturePanePng` (117–154), `sendMouse` (225–371).
**Signature:** `capturePanePng(deps, registry, id, owner): Promise<Buffer | null>`; `sendMouse(deps, registry, id, action, owner, sgrFallback): Promise<MouseResult>`.
**Data Shape:** `ResolvedTab {targetId, cdpSessionId, close()}` — existing viewer tabs are REUSED (never closed), ephemeral ones closed in `finally`. `MouseResult {ok, mode: "cdp"|"sgr", col, row, text, reason}` lets agents tell real-xterm delivery from synthesis.

### Decisive source
```ts
// :99-108 — render-landed = tab text EQUALS server-side flushed capture
const expr = `window[${JSON.stringify(LOCALTERM_PANE_TEXT_PROPERTY)}]?.() ?? null`;
while (Date.now() < deadline) {
  const expected = await registry.capturePane(id).catch(() => null);
  const tabText = await cdpClient.evaluateInSession(cdpSessionId, expr);
  if (expected !== null && tabText === expected) {
    await sleep(CDP_RENDER_LANDED_SETTLE_MS); // canvas paint
    return true;
  }
```

**Flow:** `resolveTab` finds a live page whose URL carries `?sid=<id>` before opening anything; an EPHEMERAL tab carries no browser session, so auth-gated daemons mint it a signed cookie for the owner (existing viewers already hold the user's cookie). PNG: wait until the tab's xterm text equals the server's flushed capturePane (the render-landed oracle — robust against xterm's async write), clip to `.xterm` bounds (0-size clip from an un-laid-out background tab falls back to full viewport), and retry ONCE after a settle when the first capture comes back empty. Mouse: CDP-first — read the tab's cell-metrics probe (`{left,top,cellWidth,cellHeight,cols,rows}`), default scroll to viewport center, bounds-check, then synthesize press/release with clickCount (multi-click = repeated presses + ONE release carrying final clickCount), drag press→move(buttons:1)→release, wheel as mouseWheel deltaY=±amount·cellHeight; xterm.js itself generates correct SGR so no encoder exists on this path. No reachable browser ⇒ fall back to raw SGR-1006 bytes on the PTY, gated on `registry.mouseEnabledFor(id)` so bytes never feed an app that didn't enable mouse (`reason:"mouse_disabled"`).
**Invariant:** run-tab URLs ride the LOCAL surface origin, never the tailnet (a flapping tailscale serve must not fail automation runs); every gesture reports its delivery mode so callers can distinguish synthesized from real input; tab cleanup happens in `finally` for both success and failure.
**Probe:** `packages/server/tests/session-automation.test.ts` — `"encodes a click as press + release (1-indexed)"` (:71), `"repeats the press for a multi-click"` (:75), `"encodes a drag as press + motion (button+32) + release"` (:78), `"encodes scroll as wheel button 64/65, repeated"` (:84) pin the SGR fallback encoder byte-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "capturePanePng sendMouse resolveTab", limit: 5, detail: "compact" });
// → index.ts wires them at :196; module is parse_partial at :3582 — ranges verified against raw source
```

## Verdict
Adopt the render-landed equality oracle + reuse-viewer-before-spawn + mode-reporting result shape verbatim for any browser-mediated terminal automation; adapt the cookie minting and clip selector to host DOM; omit the CDP leg entirely if your host has no embedded browser (the SGR encoder stands alone). SGR fallback pinned by direct tests at this commit; CDP legs verified against source (no upstream unit test drives a live tab).
