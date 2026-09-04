<!-- capsule-v2 -->
# Overlay bridge contract — which window.* callbacks must exist before the injected UI can talk back, and what breaks silently when one is missing?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** A page-side injected script needs Python to expose host callbacks and Python needs the page to expose entry points — what is the exact bidirectional surface, its registration order/lifetime rules (Playwright `expose_function`), and the silent-failure modes?

## Four JS→Python bridges + three Python→JS entry points; every gap is a silent no-op
**Path/Symbol:** `core/browser_manager.py:set_overlay_state_handler` (:349-353), `set_user_response_handler` (:365-367); `core/orchestrator.py:start` (:633-641); consumers `core/utils/ui/injectOverlay.js` (:358, :524, :650, :740).
**Signature:** `context.expose_function(name, handler)` ×4 — `overlay_state_changed(is_collapsed: bool)` → `overlay_state_handler`, `show_steps_state_changed(show_details: bool)` → `show_steps_state_handler`, `user_response(response: str)` → `receive_user_response`, `process_task(command: str)` → `orchestrator.receive_command`. Page side exposes globals: `window.process_task(text)`, `window.overlay_state_changed(bool)`, `window.show_steps_state_changed(bool)`.

### Decisive source
```python
# browser_manager.py :352-353 — context-scoped binding survives cross-page navigation
await context.expose_function('overlay_state_changed', self.overlay_state_handler)
await context.expose_function('show_steps_state_changed', self.show_steps_state_handler)
```
```javascript
// injectOverlay.js :389-400 collapsed click → expand; :730-746 send click → task submit
sendButton.addEventListener("click", () => {
  const text = textarea.value.trim();
  if (text && !isDisabled()) {
    if (awaitingUserResponse) { addUserMessage(text); textarea.value = ""; }
    else {
      clearOverlayMessages(); addUserMessage(text);
      disableOverlay(); window.process_task(text); textarea.value = "";
    }
    sendButton.className = "tawebagent-send-button tawebagent-send-button-disabled";
  }
});
```

**Flow:** task submission is fire-and-forget from JS (`process_task(text)` resolves immediately; `orchestrator.receive_command` resets state then awaits `run(command)` — orchestrator.py :645-650), while question answering is event-driven: Python's `prompt_user` evaluates `addSystemMessage(msg, is_awaiting_user_response=true, message_type='question')` (:473), then blocks on a local `asyncio.Event`; the JS send-branch sees module-global `awaitingUserResponse == true` and routes text through the `user_response` bridge instead of starting a new task; `receive_user_response` stores it and `.set()`s the event (browser_manager.py :444-448). Overlay/steps toggles are context-bound notifications that trigger history re-render on expand (`overlay_state_handler` :355-359).
**Invariant:** (1) `expose_function` throws "already registered" on duplicate binding for the same name/scope — register once per CONTEXT at startup, never per page/navigation (page-scoped bindings die with their page). (2) Every `window.X(...)` call site in injected code MUST have a matching `expose_function("X", ...)` or the click dies with an uncaught TypeError inside the overlay — nothing on the Python side notices; the four used names are exactly `overlay_state_changed`, `show_steps_state_changed`, `user_response`, `process_task` (verified by grep census below). (3) The awaiting-response branch never calls `disableOverlay()` — during a QUESTION the input stays enabled so the answer can be typed; only task mode disables.

**Probe:** `cd /mnt/hdd/utopia/inspo/TheAgenticBrowser && grep -o 'window\.[a-z_]*' core/utils/ui/injectOverlay.js | sort -u` → exactly `window.overlay_state_changed`, `window.process_task`, `window.show_steps_state_changed` (three distinct names; `overlay_state_changed` appears at 2 call sites :358/:524); `grep -c 'awaitingUserResponse' core/utils/ui/injectOverlay.js` → `4` (:1 init false, :733 branch test, :831 assignment — plus the grep line itself counts the declaration file-wide total 4 occurrences). No upstream tests; deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "expose_function overlay_state_changed process_task user_response", limit: 5 });
// rank-1/2: PlaywrightManager.receive_user_response core/browser_manager.py 444-448 + set_user_response_handler 365-367
```

## Verdict
Adopt the surface inventory as a checklist discipline: enumerate every window.* reference in injected code and require a matching host binding before shipping (the missing-binding failure is invisible in logs). Adapt binding scope to your driver (Playwright context vs CDP Runtime.addBinding per world). Omit nothing here — but record the two latent dead wires found while auditing this plane: `prompt_user`/`set_user_response_handler`/`command_completed` have ZERO production callers (no orchestrator path asks a question), so `awaitingUserResponse=true` is unreachable at this pin, and `ui_manager.command_completed` evaluates ghost `commandExecutionCompleted()` which exists nowhere in the JS (:240 vs grep total 0). Porters wiring an interactive loop must add both halves deliberately.
