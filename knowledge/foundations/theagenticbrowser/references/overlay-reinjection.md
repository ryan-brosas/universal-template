<!-- capsule-v2 -->
# Overlay re-injection on navigation — how does a Python-controlled chat UI survive the page it lives on being replaced?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When your agent's user interface is injected INTO the pages it automates, how do you keep state and history across every navigation?

## Class-level UI state + domcontentloaded re-inject + guarded full replay
**Path/Symbol:** `core/utils/ui_manager.py`:`UIManager.handle_navigation` (`:42-69`), class attrs (`:26-32`), `update_overlay_chat_history` (`:124-181`); wiring `core/browser_manager.py`:`set_navigation_handler` (`:343-347`), `notify_user` prefix ladder (`:370-422`); JS `core/utils/ui/injectOverlay.js` (941L; entry `init()` :933, `addSystemMessage` :826, `clearOverlayMessages` :874, `process_task` bridge :740).
**Signature:** `async def handle_navigation(self, frame: Frame)`; `def new_system_message(self, message: str, type: MessageType = MessageType.STEP)`.
**Data Shape:** Conversation history is a CLASS attribute list of `{"from": "user"|"system", "message", "message_type"}` — shared by every UIManager instance (there is only one). Overlay state: `overlay_is_collapsed`, `overlay_show_details`, `overlay_processing_state ∈ {init, processing, done}` all class-level.

### Decisive source
```python
async def handle_navigation(self, frame):
    await frame.wait_for_load_state("load")
    js_code = open(os.path.join(PROJECT_SOURCE_ROOT,"core","utils","ui","injectOverlay.js")).read()
    await frame.evaluate(js_code)                       # full re-injection on EVERY nav
    if self.overlay_is_collapsed:
        await frame.evaluate(f"showCollapsedOverlay('{self.overlay_processing_state}', {js_bool});")
    else:
        await frame.evaluate(f"showExpandedOverlay('{self.overlay_processing_state}', {js_bool});")
    await self.update_overlay_chat_history(frame)       # then replay ALL history
except Exception as e:
    if "Frame was detached" not in str(e): raise e      # detach during nav is normal

# notify_user prefixes by type before sending: PLAN -> beautified "Plan:\n...",
# STEP -> "Next step: ..." (or "Verify: ..." when text contains 'confirm'),
# QUESTION/ANSWER similarly; STEP visibility obeys overlay_show_details.
```
Replay guard: `__update_overlay_chat_history_running` name-mangled flag blocks concurrent replays; each system message re-sent via `addSystemMessage(json.dumps(msg), false, type_json)` with one fallback to default type; STEP-type messages are filtered out entirely when show_details=False.
**Flow:** domcontentloaded → handle_navigation → inject file → restore collapsed/expanded + processing state → clearOverlayMessages → loop-replay history → exposed bridges (`process_task`, `overlay_state_changed`, `user_response`) reconnect Python to the fresh DOM.
**Invariant:** State MUST live Python-side (class attrs), never in the DOM — the DOM dies at every navigation. Frame-detach during injection is an expected race, not an error. Two escape-hatch sanitizers run on every outbound message: strip leading ':' and trailing ',' (LLM output artifacts). Known upstream quirk for porters: `show_overlay` sets `self.overlay_is_collapsed = True` AFTER evaluating showExpandedOverlay — inverted flag, benign only because update_overlay_state callbacks correct it later; do NOT copy that line.
**Probe:** No tests (coverage caveat). Graph pins: `trace_path --function-name handle_navigation --direction inbound` resolves through PlaywrightManager.set_navigation_handler's domcontentloaded registration; `process_task` exposure wired in Orchestrator.start GUI_ONLY branch (`orchestrator.py:638-640`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "overlay handle_navigation chat history inject", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt Python-owned UI state with per-navigation re-injection and serialized replay. Adapt the overlay id/styles. Omit the inverted-flag quirk (fix it) and the dual MessageType modules — consolidate to one enum in your port.
