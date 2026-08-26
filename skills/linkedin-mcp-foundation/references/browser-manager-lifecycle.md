<!-- capsule-v2 -->
# BrowserManager lifecycle — one funnel, refusals at the door, confirmed close before handover

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** When every browser in a process launches through one class, which overrides must be refused, and what must be proven before the profile may change hands?

## BrowserManager.start / close / close_confirmed
**Path/Symbol:** `linkedin_mcp_server/core/browser.py` — `BrowserManager` (:62-720); funnel refusals (:84-102), `_geometry` (:161-178), windowless decision (:145-159), start ladder (:215-429), `close` (:431-486), `_await_deferring_cancels` (:44-59), cookie export/import (:545-715).
**Signature:** `async def start() -> None`; `async def close() -> bool` (confirmed?); `close_confirmed -> bool`; `BrowserManager(user_data_dir, headless=True, slow_mo=0, viewport=None, **launch_options)`.
**Data Shape:** `viewport` kept as passed INCLUDING `None` (the old `viewport or {...}` made "no viewport" unexpressable → measured headed window larger than its own reported screen).

### Decisive source
```python
# :84-89 — the one funnel refuses identity overrides outright
if "user_agent" in launch_options:
    raise TypeError("BrowserManager does not accept a user_agent. The browser "
        "reports its own identity; an override changes the string but not the "
        "client hints, and never reaches service workers.")

# :240-244 — downgrade refusal BEFORE the profile dir is touched; off-loop
await asyncio.to_thread(refuse_a_downgrade,
                        Path(self.user_data_dir),
                        self._executable_about_to_run())
secure_mkdir(Path(self.user_data_dir))

# :378-390 — even a CANCELLED launch is cleaned, result kept, not re-raised
closed = await _await_deferring_cancels(self.close())
if not closed:
    raise BrowserShutdownUnconfirmedError(...)   # profile is kept, not handed on
```
**Flow:** refuse `user_agent`/`no_viewport` → start driver (attach flag only when a hidden target will actually be created) → downgrade refusal pre-creation → secure mkdir/harden → launch persistent context; headed attempt on a display-less host ⇒ mark per-instance flag, bounded-stop old driver (the attach flag lives in the DRIVER process for life — replace it, don't restore env), relaunch headless, retry failure logged then FIRST error raised `from None` → page = hidden target or startup page. Any failure path: cancel-deferring close; `BrowserDowngradeError` re-raised AHEAD of shutdown-unconfirmed so a refusal is never masked as a wedge.
**Invariant:** Cleanup steps are bounded (10 s) and fail SOFT but RECORDED: `close()` returns whether shutdown was confirmed, and no caller may release/delete/hand over the profile while `close_confirmed` is false (lease integration pins it). Geometry is decided by the ACTUAL launch mode here, not by configuration — the pure options builder cannot know the login will pass `headless=False`.
**Probe:** `tests/test_core_browser.py` — :16-41 pin both constructor refusals; `TestGeometry` (:44-91) pins mode-decided keys; `TestTheWindowlessLaunchEndToEnd` (:226+) drives the fallback ladder end to end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "BrowserManager close confirmed profile handover", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the funnel-with-refusals pattern (dangerous kwargs raise instead of being dropped), pre-mutation invariant checks off-loop, per-instance learned capability flags, and confirmed-close gating for any persistent-profile browser manager. Adapt timeouts and platform fallbacks. Omit Patchright driver internals. Coverage caveat: none — module fully indexed.
