<!-- capsule-v2 -->
# Navigation reinjection & history replay — how does the overlay come back after every page load with its full transcript, without duplicate renders or races?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** A Python-owned UI injected into a hostile page dies on every navigation — what is the re-injection + replay protocol, and which guards prevent the three classic failures (double-inject, concurrent replay, lost messages)?

## domcontentloaded hook → whole-file evaluate → state restore → guarded full replay
**Path/Symbol:** `core/utils/ui_manager.py:handle_navigation` (:42-69), `update_overlay_chat_history` (:124-181); wiring `core/browser_manager.py:345` (`page.on("domcontentloaded", self.ui_manager.handle_navigation)`); page-side `clearOverlayMessages` (injectOverlay.js :874-881).
**Signature:** `async handle_navigation(frame: Frame)`; `async update_overlay_chat_history(frame_or_page: Frame | Page)`; guard flag `__update_overlay_chat_history_running: bool`.

### Decisive source
```python
# ui_manager.py :50-65 — inject file body, then RESTORE view+state, then replay
await frame.wait_for_load_state("load")
overlay_injection_file = os.path.join(PROJECT_SOURCE_ROOT,"core","utils","ui","injectOverlay.js")
with open(overlay_injection_file, 'r') as file:
    js_code = file.read()
await frame.evaluate(js_code)
js_bool = str(self.overlay_show_details).lower()
if self.overlay_is_collapsed:
    await frame.evaluate(f"showCollapsedOverlay('{self.overlay_processing_state}', {js_bool});")
else:
    await frame.evaluate(f"showExpandedOverlay('{self.overlay_processing_state}', {js_bool});")
await self.update_overlay_chat_history(frame)
```
```python
# :128-132 + finally:181 — non-reentrant replay via bool latch
if self.__update_overlay_chat_history_running:
    logger.debug("update_overlay_chat_history is already running, returning" + frame_or_page.url)
    return
self.__update_overlay_chat_history_running = True
try:
    ...
finally:
    self.__update_overlay_chat_history_running = False
```

**Flow:** every `domcontentloaded` → wait `load` → read injectOverlay.js from disk and `frame.evaluate` it (the file's own tail runs `init()` → styles + collapsed overlay) → push mirrored state so the restored view matches pre-navigation mode/state → if expanded, wipe DOM children and replay the ENTIRE `conversation_history` list message-by-message. Replay details that porters lose: user messages bypass the show_details filter (:156 comment "Only filter system messages"); STEP-type system messages are dropped at replay time when `overlay_show_details` is false; per-message evaluate failures fall back to a `'step'`-type retry then log-and-continue — one bad message never kills the replay.
**Invariant:** (1) Python owns ALL durable UI state as a plain mirror; JS keeps none across navigations — any new UI feature must add its state to the Python mirror AND to the restore sequence or it resets on navigation. (2) The injection order is load-bearing: script first (defines functions), then view/state restore, then history replay — calling `addSystemMessage` before the script evaluates throws and aborts the handler. (3) The boolean latch makes replay single-flight; without it, rapid navigation bursts run interleaved replays against two freshly-built chat boxes and duplicate messages. (4) Navigation-during-raise: only "Frame was detached" errors are swallowed (:68) — everything else re-raises, so real bugs stay visible.

**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -n 'await frame.evaluate(js_code)' core/utils/ui_manager.py` → `57`; `grep -c '"Frame was detached" not in str(e)' core/utils/ui_manager.py` → `1`; `grep -c '__update_overlay_chat_history_running' core/utils/ui_manager.py` → `5` (docstring :23, decl :32, guard :128, set :132, finally-reset :181). No upstream tests; deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "handle_navigation inject frame", limit: 4 });
// rank-1: UIManager.handle_navigation core/utils/ui_manager.py 42-69
```

## Verdict
Adopt the event-driven re-injection pattern (Python-side file read + evaluate beats add_init_script here because it also restores STATE and replays in one hook) with the single-flight latch and swallow-only-detached error policy. Adapt the disk read to packaged resources in frozen apps. Omit nothing — but note the known race: `show_overlay`'s inverted flag write (`ui_manager.py:83`, recorded quirk) can desync the mirror until the next navigation heals it, since the DOM click path reports truth back through `overlay_state_changed`. Coverage caveat: no upstream tests; behavior pinned by line-exact greps.
