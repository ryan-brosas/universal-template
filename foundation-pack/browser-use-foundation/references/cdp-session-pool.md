<!-- capsule-v2 -->
# Browser session — event-driven CDP target pool + resilient event bus

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does a browser session survive tab crashes, detaches, and torn-down event loops while keeping one stable "agent focus"?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/session.py` (4,133 lines): `Target` (:73), `CDPSession` (:88), `ResilientEventBus` (:106-131), `BrowserSession` (:134) — `get_or_create_cdp_session` (:1472-1560), `attach_all_watchdogs` (:1680), `get_browser_state_summary` (:1587), `connect` (:1831), lifecycle handlers (`on_BrowserStartEvent` :778, `on_NavigateToUrlEvent` :897, `on_SwitchTabEvent` :1131); `browser/session_manager.py`: `SessionManager` (:19) monitoring `attachedToTarget`/`detachedFromTarget`/`targetInfoChanged` CDP events (:82-112).
**Signature:** `get_or_create_cdp_session(target_id?, focus=True)` — sessions are NOT created here; Chrome auto-attaches them (`autoAttach=True`) into the pool; this method waits for the attach event (poll 20×100ms), validates liveness, and only switches focus to `page`-type targets.
**Data Shape:** pools keyed by `TargetID` → `CDPSession` and `SessionID`; per-target lifecycle-event deque; focus = single `agent_focus_target_id`.

### Decisive source
```ts
# ResilientEventBus: no-op instead of assert when bus is torn down
class ResilientEventBus(EventBus):
    async def step(self, event=None, ...):
        if self._on_idle is None or self.event_queue is None: return None   # warm-resume safe
        return await super().step(event, ...)
# get_or_create_cdp_session:
if target_id is None:
    focus_valid = await self.session_manager.ensure_valid_focus(timeout=5.0)  # centralized recovery
    if not focus_valid: raise ValueError('No valid agent focus - unstable state')
session = self.session_manager._get_session_for_target(target_id)
if not session:
    for attempt in range(20):            # wait for Chrome's Target.attachedToTarget
        await asyncio.sleep(0.1); session = ...
        if session: break
if focus and self.agent_focus_target_id != target_id:
    if target_type != 'page': refuse     # NEVER focus iframes/workers
```

**Flow:** connect → CDP `Target.setAutoAttach` makes Chrome push sessions into the pool as targets appear → SessionManager tracks attach/detach/info-changed events and per-target lifecycle history → consumers ask `get_or_create_cdp_session`, which centralizes focus validation, attach-waiting, and liveness checks → watchdogs attach to the same bus. The ResilientEventBus subclass makes post-teardown `step()`/`wait_until_idle()` no-ops so serverless warm resumes don't crash.
**Invariant:** exactly one agent focus, only ever a page-type target; sessions come from Chrome's events (single source of truth) rather than manual creation; a torn-down bus degrades to no-op instead of asserting; every session use re-validates liveness.
**Probe:** `tests/` session tests (auto-attach pool populated; detach invalidates + recovers focus; iframe focus refused; resilient bus no-ops after teardown).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "get_or_create_cdp_session SessionManager attachedToTarget ResilientEventBus agent_focus", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the auto-attach session pool with a single validated focus and event-driven liveness; subclass the bus to make teardown idempotent. Adapt pooling to host transport.
