<!-- capsule-v2 -->
# Message injection & escaping ladder — how does a Python string reach the overlay chat as a quoted, line-broken literal without breaking the JS f-string?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When the host builds `page.evaluate` code by string interpolation (no argument binding), what is the minimal escaping contract for arbitrary LLM/user text, and which of the two competing escapers must run at which layer?

## json.dumps at the replay layer; quote-escape + <br> at the live layer
**Path/Symbol:** `core/utils/js_helper.py:escape_js_message` (:6-16); consumers `core/browser_manager.py:notify_user` (:403-418), `prompt_user` (:471-474); replay layer `core/utils/ui_manager.py:update_overlay_chat_history` (:142-161); final sink `core/utils/ui/injectOverlay.js:addMessage` (:782-783).
**Signature:** `escape_js_message(message: str) -> str` — returns a QUOTED JS string literal; `json.dumps(str(message["message"]))` likewise yields a quoted literal.

### Decisive source
```python
# js_helper.py :11-16 — newline→<br> FIRST, then quote escaping, wrap in quotes
message = message.replace('\n', '<br>')
# Escape quotes and wrap in quotes
message = message.replace('"', '\\"')
return f'"{message}"'
```
```python
# ui_manager.py :142,146,161 — history replay uses json.dumps instead
message_content = json.dumps(str(message["message"]))
...
js_code = f"addSystemMessage({message_content}, false, {message_type_json});"
```
```javascript
// injectOverlay.js :782-783 — page side strips surrounding quotes then injects as HTML
const cleanMessage = message.replace(/^"|"$/g, "");
messageBubble.innerHTML = cleanMessage;
```

**Flow:** every producer composes `f"addSystemMessage({literal}, ...)"` where `{literal}` is ALREADY a complete JS string expression produced by one of the two escapers; the page-side sink strips exactly ONE pair of leading/trailing double quotes and assigns to `.innerHTML`. Live pushes (`notify_user`, `prompt_user`) use `escape_js_message`; bulk replay after navigation uses `json.dumps`. Both layers exist because they fail differently: `escape_js_message` converts newlines to `<br>` (visual line breaks inside innerHTML) but leaves backslashes and `<script>`-shaped content untouched; `json.dumps` is a correct JSON-string encoder for quotes/newlines/backslashes but emits `\n` escapes that render as nothing in HTML.
**Invariant:** (1) NEVER interpolate raw Python strings into evaluate code — the value must arrive pre-quoted or the generated JS is a syntax error and the evaluate throws. (2) Double-escaping produces visibly wrong output (`\"` rendered literally), so each pipeline stage must use exactly one escaper; mixing both on one value is the classic corruption bug. (3) The message AND its type enum go through escaping separately before composition (`safe_message_type = escape_js_message(message_type.value)` browser_manager.py :414). (4) Because the sink is `.innerHTML`, any HTML in the text renders — this is a deliberate rich-text choice that doubles as an XSS hole when pages influence message content; porters MUST switch the sink to `textContent` unless rich rendering is required.

**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -c "replace('\\\\n', '<br>')" core/utils/js_helper.py` → `1` and `grep -c 'json.dumps(str(message' core/utils/ui_manager.py` → `2` and `grep -n 'messageBubble.innerHTML = cleanMessage' core/utils/ui/injectOverlay.js` → `783`. No upstream tests; deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "escape_js_message beautify_plan_message", limit: 4 });
// rank-1: core.utils.js_helper.escape_js_message core/utils/js_helper.py 6-16
```

## Verdict
Adopt the two-layer rule: JSON-encode anything crossing a serialization boundary (replay/history), minimal quote+newline escaping only for immediate same-page evaluate — and always compose f-strings from pre-quoted literals. Adapt the `<br>` conversion if your sink is textContent (then prefer json.dumps everywhere). Omit the illusion of safety: this ladder prevents SYNTAX breakage, not injection — treat innerHTML as a known hazard to fix on port. Coverage caveat: no upstream tests exercise adversarial input; pins are line-exact greps only.
