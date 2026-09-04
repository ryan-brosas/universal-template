<!-- capsule-v2 -->
# Watchdog pattern — convention-bound event handlers with CDP circuit breaker

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does a long-lived browser session self-heal (crashes, popups, captcha, downloads) without one giant god-object managing it?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdog_base.py` (321 lines): `BaseWatchdog` (:15) — `LISTENS_TO`/`EMITS` ClassVars (:33-34), `attach_handler_to_session` (:56-223), `attach_to_session` (:243-291), `__del__` task cleanup (:293); 14 concrete watchdogs in `browser/watchdogs/` (`crash_watchdog.py`, `popups_watchdog.py`, `captcha_watchdog.py`, `downloads_watchdog.py`, ...).
**Signature:** a watchdog declares handlers by NAME convention — `on_EventTypeName(self, event)` — and `attach_to_session()` discovers + registers them via reflection, asserting each is declared in `LISTENS_TO`.
**Data Shape:** pydantic BaseModel with `extra='forbid'` (all state must be typed Fields or PrivateAttrs); deps injected as Fields (`event_bus`, `browser_session`); internal tasks as PrivateAttr `_foo_task`/`_bar_tasks` so `__del__` can cancel them.

### Decisive source
```ts
# handler naming convention: on_EventTypeName -> auto-registered to the event bus
assert handler.__name__.startswith('on_') and handler.__name__.endswith(event_class.__name__)
# circuit breaker inside every generated wrapper:
if event.event_type not in LIFECYCLE_EVENT_NAMES and not browser_session.is_cdp_connected:
    if browser_session.is_reconnecting:
        await asyncio.wait_for(browser_session._reconnect_event.wait(), timeout=...)
        if not connected: raise ConnectionError(...)
    else: return None            # intentional stop: silent skip
# on handler failure: try to re-acquire the CDP session for the focused target,
# then ALWAYS re-raise the original error with traceback preserved
# __del__ magic: cancel any attr named _*_task or iterated *_tasks
```

**Flow:** session starts → all watchdogs attach (reflection finds `on_*` methods) → event bus dispatches browser events → each wrapper checks CDP health first (skip / wait-for-reconnect), runs the handler with timing logs, and on failure attempts CDP session re-creation before re-raising. Lifecycle events (start/stop/kill/reconnect) bypass the breaker since they ARE the recovery path.
**Invariant:** handlers never hang on a dead WebSocket (circuit breaker + reconnect wait); duplicate registration raises; original errors keep their tracebacks; watchdog state is either typed fields or cancellable `_task` privates.
**Probe:** `tests/` watchdog tests (handler auto-discovery; LISTENS_TO assertion; crash watchdog recovers after kill; duplicate attach raises).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "BaseWatchdog attach_to_session LISTENS_TO circuit breaker crash popup captcha", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt convention-registered watchdogs over a monitor god-object; copy the CDP-style circuit breaker + lifecycle exemption + task-canceling `__del__`. Adapt the event bus to host.
