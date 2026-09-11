<!-- capsule-v2 -->
# About:blank keep-alive + DVD screensaver — how does a browser session guarantee it never closes its last tab?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you keep a Chrome instance alive when the agent closes every tab, and what does a watchdog do about a dead CDP connection?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/aboutblank_watchdog.py` whole (259L) — `AboutBlankWatchdog` (:16), `on_TabClosedEvent` (:48), `_check_and_ensure_about_blank_tab` (:76), `_show_dvd_screensaver_on_about_blank_tabs` (:95), `_show_dvd_screensaver_loading_animation_cdp` (:110).
**Signature:** `LISTENS_TO = [BrowserStopEvent, BrowserStoppedEvent, TabCreatedEvent, TabClosedEvent]`; `EMITS = [NavigateToUrlEvent, CloseTabEvent, AboutBlankDVDScreensaverShownEvent]`.

### Decisive source
```python
async def on_TabClosedEvent(self, event):
    if self._stopping: return                    # never create tabs during shutdown
    # Don't attempt CDP operations if the WebSocket is dead — dispatching
    # NavigateToUrlEvent on a broken connection will HANG until timeout
    if not self.browser_session.is_cdp_connected:
        self.logger.debug('[AboutBlankWatchdog] CDP not connected, skipping tab recovery')
        return
    page_targets = await self.browser_session._cdp_get_all_pages()
    if len(page_targets) < 1:
        # Last tab closing -> create about:blank BEFORE the close lands,
        # else Chromium exits and the whole session dies.
        navigate_event = self.event_bus.dispatch(NavigateToUrlEvent(url='about:blank', new_tab=True))
        await navigate_event
```
```javascript
// Injection is IDEMPOTENT on three axes:
if (window.__dvdAnimationRunning) return;          // re-entry latch
if (!document.body) { /* reset latch; retry on DOMContentLoaded */ }
const animated_title = `Starting agent ${label}...`;
if (document.title === animated_title) return;     // already-run marker via title
```

**Flow:** TabCreated with about:blank URL → screensaver injected into ALL about:blank targets via non-focused cached CDP sessions → TabClosed pre-event checks remaining pages and pre-seeds a fresh about:blank tab when this was the last → BrowserStop/Stopped set `_stopping` so recovery halts during teardown.
**Invariant:** the last-tab check runs on the PRE-close event (post-close is too late — Chromium already exited); every CDP dispatch is gated on `is_cdp_connected` because event-bus sends on a dead socket hang until the timeout ladder fires; injection must be idempotent since TabCreated can fire multiple times per tab.
**Probe:** deterministic source/graph probe only (coverage caveat: no dedicated test file); behavior pinned by LISTENS_TO/EMITS contract in graph + `is_cdp_connected` gate cited at :53.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "AboutBlankWatchdog TabClosedEvent _cdp_get_all_pages dvd screensaver idempotent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pre-close last-tab seeding rule + connection-gated recovery + idempotent overlay injection; adapt or omit the DVD animation itself (cosmetic); keep the `_stopping` shutdown gate.
