<!-- capsule-v2 -->
# User-notification message protocol — how do overlay messages get prefixed, escaped, and gated before reaching the page?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** What is the full journey of a status message from Python to the injected overlay, and which gates decide whether the user ever sees it?

## Type-keyed prefixing → JS-string escaping → detail-gated evaluate → listener fan-out
**Path/Symbol:** `core/browser_manager.py`:`PlaywrightManager.notify_user` (`:370-422`); escape helper `core/utils/js_helper.py:escape_js_message` (`:6-16`); plan beautifier `js_helper.beautify_plan_message` (`:19-33`); fan-out `core/utils/notification.py:NotificationManager` (`:4-53`).
**Signature:** `async def notify_user(self, message: str, message_type: MessageType = MessageType.STEP)`.
**Data Shape:** `MessageType` enum values PLAN/STEP/QUESTION/ANSWER/INFO/ERROR/USER_QUERY. Listener payload is a dict `{"message": ..., "type": ...}`. The overlay JS entrypoint signature is `addSystemMessage(<quoted>, is_awaiting_user_response=false, message_type=<quoted>)`.

### Decisive source
```python
# :384-397 — silent input sanitation THEN type-keyed prefixing
if message.startswith(":"):
    message = message[1:]
if message.endswith(","):
    message = message[:-1]
if message_type == MessageType.PLAN:
    message = beautify_plan_message(message)      # newline before every " N." step
    message = "Plan:\n" + message
elif message_type == MessageType.STEP:
    if "confirm" in message.lower():
        message = "Verify: " + message            # substring match, not word match!
    else:
        message = "Next step: " + message
...
# :403-404, :414-418 — quote-wrap BOTH args before f-string JS assembly
safe_message = escape_js_message(message)          # \n→<br>, "→\", wrapped in quotes
self.ui_manager.new_system_message(safe_message, message_type)
...
safe_message_type = escape_js_message(message_type.value)
js_code = f"addSystemMessage({safe_message}, is_awaiting_user_response=false, message_type={safe_message_type});"
await page.evaluate(js_code)
```
**Flow:** early-return when no ui_manager (headless/API mode never touches the DOM) → strip leading `:` and trailing `,` (LLM output hygiene) → prefix per type → record in UI conversation history → DETAIL GATE (:406-412): when `overlay_show_details` is False only PLAN/QUESTION/ANSWER/INFO reach the page — STEP messages are history-recorded but NOT displayed; when True all five pass → `page.evaluate` the assembled JS (failure logged as "will work itself out after the page loads", never raised :419-420) → `notification_manager.notify(message, message_type.value)` fans out to registered listeners (empty-listener case prints a discard notice; SSE bridge registers its queue-drain listener here).
**Invariant:** Escape at the LAST moment before string-assembled JS — both the message AND the enum value are quote-wrapped by `escape_js_message`; newlines must become `<br>` because they travel inside an HTML-ish JS string. The `"confirm"` check is a raw substring test (`"Confirm your email"` → Verify-prefixed; any step merely CONTAINING "confirm" too). The evaluate failing must not fail the pipeline — notifications are best-effort by design.
**Probe:** `grep -n 'message.startswith(":")' core/browser_manager.py` → `384`; `grep -c '"confirm" in message.lower()' core/browser_manager.py` → `1`; `grep -n 'overlay_show_details == False' core/browser_manager.py` → `406`; `grep -c "addSystemMessage(" core/browser_manager.py` → `2` (:416 + prompt_user's awaiting-response variant :473); `grep -n "beautify_plan_message(message)" core/browser_manager.py` → `391`. Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "notify_user addSystemMessage escape_js_message message_type", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: type-keyed prefix ladder, last-moment JS escaping of value AND key, detail-gated display with always-on history, best-effort evaluate. Adapt: prefix wording ("Verify:"/"Next step:") and overlay ids. Omit: NotificationManager print fallback in production. Coverage caveat: no upstream tests; probes line-pinned at pin `71daa28`.
