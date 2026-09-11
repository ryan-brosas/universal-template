<!-- capsule-v2 -->
# Event-tap monkeypatch — how do you add dialog capture and load-triggered side effects to a third-party WS client without forking it?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Where do you hook a library's event stream when it offers no observer API, and which work belongs on the synchronous tap path?

## handle_event wrapper: ring buffer + dialog latch + fire-and-forget reactions
**Path/Symbol:** `src/browser_harness/daemon.py:Daemon.start` tap installation (:531-542); ring `self.events = deque(maxlen=BUF=500)` (:367).
**Signature:** replaces `cdp._event_registry.handle_event` with `async def tap(method, params, session_id=None)` ending in `return await orig(...)`.
**Data Shape:** buffered entries `{"method", "params", "session_id"}`; drained wholesale by clients via `{"meta":"drain_events"}` → `{"events":[...]}` then cleared.

### Decisive source
```python
orig = self.cdp._event_registry.handle_event
mark_js = "if(!document.title.startsWith('🐴'))document.title='🐴 '+document.title"
async def tap(method, params, session_id=None):
    self.events.append({"method": method, "params": params, "session_id": session_id})
    if method == "Page.javascriptDialogOpening": self.dialog = params   # latch
    elif method == "Page.javascriptDialogClosed": self.dialog = None
    elif method in ("Page.loadEventFired", "Page.domContentEventFired"):
        # side effect must NOT delay dispatch of the original event
        asyncio.create_task(_silent(asyncio.wait_for(
            self.cdp.send_raw("Runtime.evaluate", {...}, session_id=self.session), timeout=2)))
    return await orig(method, params, session_id)      # ALWAYS forward last
self.cdp._event_registry.handle_event = tap
```

**Flow:** wrap → record into bounded deque → update dialog state machine → spawn silent timed side-effect tasks on page-load events → delegate to the original handler unconditionally.
**Invariant:** the wrapper forwards EVERYTHING even if its own logic throws paths are guarded (`_silent` swallows; timeouts cap at 2s); buffer is fixed-size (500) so a slow consumer loses oldest events rather than growing memory; consumers filter by `session_id` themselves (background tabs keep emitting).
**Probe:** no direct unit test for the tap (requires live CDP) — coverage caveat; adjacent pins: `tests/unit/test_daemon.py:250` current_tab meta path and drain contract used by helpers' `wait_for_network_idle`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "handle_event tap javascriptDialogOpening drain_events", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the wrapper shape (bounded ring + state latch + fire-and-forget effects + unconditional delegation) whenever a dependency lacks hooks; adapt trigger methods/effects; omit CDP details. Coverage caveat noted in-capsule.
