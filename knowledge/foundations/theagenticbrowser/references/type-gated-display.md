<!-- capsule-v2 -->
# Type-keyed display gating — which message types render when "show details" is off, and why do live push and replay disagree?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When porting a chat-style agent UI with a details/verbose toggle, where should visibility be decided — producer, live renderer, or replay renderer — and how do you keep the three from drifting?

## Three enforcement sites, one allowlist, two divergent copies of it
**Path/Symbol:** `core/browser_manager.py:notify_user` (:406-412); `core/utils/ui_manager.py:update_overlay_chat_history` (:156-157); page side `core/utils/ui/injectOverlay.js:addMessage` (:756-759) + toggle handler (:634-651).
**Signature:** `MessageType` enum values: `plan|step|action|answer|question|info|final|transaction_done|error|max_turns_reached` (`core/utils/message_type.py:4-15`); `addMessage(message, sender, message_type = "plan")`.
**Data Shape:** `overlay_show_details: bool` mirrored Python-side; per-message `data-message-type` attribute on the wrapper div.

### Decisive source
```python
# browser_manager.py :406-412 — LIVE gate: STEP suppressed when details off
if self.ui_manager.overlay_show_details == False:
    if message_type not in (MessageType.PLAN, MessageType.QUESTION, MessageType.ANSWER, MessageType.INFO):
        return
if self.ui_manager.overlay_show_details == True:
    if message_type not in (MessageType.PLAN, MessageType.QUESTION, MessageType.ANSWER, MessageType.INFO, MessageType.STEP):
        return
```
```python
# ui_manager.py :156-157 — REPLAY gate re-implements the filter
if not self.overlay_show_details and message_type == MessageType.STEP.value:
    continue
```
```javascript
// injectOverlay.js :756-759 — RENDER-time gate at creation
messageContainer.style.display =
  sender === "user" || message_type !== "step" || show_details ? "flex" : "none";
```

**Flow:** a system message passes if (producer allowlist) AND (renderer check) both accept it. With details OFF the visible set is exactly {plan, question, answer, info} (+ user messages always). With details ON everything renders including step/action/error/final. The toggle switch flips `show_details`, then re-walks the DOM flipping only `data-message-type="step"` wrappers between flex/none and notifies Python via `window.show_steps_state_changed`.
**Invariant:** (1) User messages are NEVER filtered at any layer. (2) The live producer allowlist names FIVE non-displayed types as suppressed-when-details-off, while the replay filter drops ONLY `step` — so an `error` or `final` pushed live while details are off is suppressed, but the SAME history replays them after navigation. This divergence is shipped behavior, not a transcription error; decide deliberately whether to unify on the strict allowlist. (3) The enum value that reaches JS must be escaped separately (see message-injection capsule); type strings are matched by equality in three languages — rename a value in Python and all three gates silently change meaning.

**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -c 'data-message-type' core/utils/ui/injectOverlay.js` → `2` (setAttribute :763 + toggle read :644); `grep -n 'Only filter system messages, not user messages' core/utils/ui_manager.py` → `155`; `grep -n 'MessageType.STEP' core/browser_manager.py` → 4 lines (:370 default param, :393 prefix gate, :411 details-on allowlist, :555 log_system_message default). No upstream tests; deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "notify_user message type prefix", limit: 4 });
// rank-1: PlaywrightManager.notify_user core/browser_manager.py 370-422; rank-2: MessageType class 4-15
```

## Verdict
Adopt: visibility decided at BOTH producer (cheap suppress) and renderer (toggle without rebuild), keyed off a single string enum carried as a data attribute; always-exempt user messages. Adapt: collapse the two Python filters into one shared predicate on port — but first record that upstream's divergence means replay is MORE verbose than live; unifying changes what users see after navigation. Omit the duplicated `ui_messagetype.py` enum twin (missing USER_QUERY; already recorded as a known quirk in pass 2's Boundaries).
