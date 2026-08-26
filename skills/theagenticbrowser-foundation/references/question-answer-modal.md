<!-- capsule-v2 -->
# Question/answer modal protocol — how does Python block on a human answer typed into an injected page UI, and why is the wiring dead at this pin?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** What is the full coroutine-suspension path for asking the user a question through the overlay (show → await event → bridge → resume), which side sets/clears state, and what must a porter add to make it live?

## asyncio.Event handshake across the JS bridge; every link present, zero callers
**Path/Symbol:** `core/browser_manager.py:prompt_user` (:451-482), `receive_user_response` (:444-448), `set_user_response_handler` (:365-367); page side `core/utils/ui/injectOverlay.js:setupEventListeners` send branch (:730-746) + `addSystemMessage` awaiting latch (:831).
**Signature:** `async def prompt_user(self, message: str) -> str`; `async def receive_user_response(self, response: str)`; state: `self.user_response: str`, `self.user_response_event = asyncio.Event()`.
**Data Shape:** question renders via `addSystemMessage(<quoted>, is_awaiting_user_response=true, message_type='question')`.

### Decisive source
```python
# browser_manager.py :473-481 — open overlay, ask, suspend, consume
js_code = f"addSystemMessage({safe_message}, is_awaiting_user_response=true, message_type='question');"
await page.evaluate(js_code)
await self.user_response_event.wait()
result = self.user_response
self.user_response_event.clear()
self.user_response = ""
self.ui_manager.new_user_message(result)
return result
```
```javascript
// injectOverlay.js :733-742 — module-global latch routes the reply to the bridge
if (awaitingUserResponse) {
  addUserMessage(text);            // echo only — NO process_task call
  textarea.value = "";
} else {
  clearOverlayMessages(); addUserMessage(text);
  disableOverlay(); window.process_task(text); textarea.value = "";
}
```

**Flow:** `prompt_user` forces expanded view (`show_overlay`), logs QUESTION into history, evaluates the awaiting-form message (page-side latch `awaitingUserResponse = true` at :831), then suspends on `user_response_event.wait()`; when the user hits send, the awaiting branch echoes locally and calls the exposed `user_response(text)` bridge; `receive_user_response` stores the string and `.set()`s the event; Python resumes, clears event+buffer, records the answer as a user message in history.
**Invariant:** (1) Exactly one pending question at a time — the single Event + single string slot cannot represent two concurrent asks; serialize callers. (2) State reset happens AFTER resume (`clear()` then buffer wipe at :479-480) so a second `wait()` can never observe the stale set from the previous round-trip. (3) During awaiting, input stays ENABLED (no disableOverlay in that branch) — contrast with task mode which disables until completion. (4) DEAD AT THIS PIN: grep census finds no caller of `prompt_user` anywhere under core/, and while `set_user_response_handler` registers the bridge, no production flow ever sets `awaitingUserResponse=true` — the only writer would be this uncalled method. Porters get a complete, coherent pattern that must be deliberately activated.

**Probe:** `cd /mnt/hdd/utopia/inspo/TheAgenticBrowser && grep -rn 'prompt_user(' --include='*.py' . | grep -v 'async def'` → EMPTY (zero callers); `grep -c "is_awaiting_user_response=true, message_type='question'" core/browser_manager.py` → `1` (:473); `grep -n 'awaitingUserResponse' core/utils/ui/injectOverlay.js` → 4 lines (:1 false init, :733 branch test, :831 assignment). No upstream tests; deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "prompt_user question awaiting response event", limit: 4 });
// rank-1: PlaywrightManager.prompt_user core/browser_manager.py 451-482
```

## Verdict
Adopt the pattern wholesale for HITL ports: overlay-forced expansion, awaiting-latch routing, single Event handshake with post-resume reset. Adapt the asyncio.Event to your runtime's suspension primitive. Omit nothing — but ship the activation work upstream skipped: a caller site (e.g. critique agent emitting MessageType.QUESTION), plus wire `ui_manager.command_completed`'s ghost evaluate (`commandExecutionCompleted()`, undefined in JS :240) to a real page function or drop it.
