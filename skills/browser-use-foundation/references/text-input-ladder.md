<!-- capsule-v2 -->
# Text-input ladder — clear, focus, React-native-setter, char typing, readback, auto-retry

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does an agent reliably type text into arbitrary inputs (including React/Vue controlled components, date pickers, contenteditable) over CDP?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/default_action_watchdog.py`: `DefaultActionWatchdog._input_text_element_node_impl` (:1756-2088), `_clear_text_field` (:1344-1558), `_focus_element_simple` (:1560-1615), `_requires_direct_value_assignment` (:1617-1667), `_set_value_directly` (:1669-1754), `_trigger_framework_events` (:2090-2202), `_get_char_modifiers_and_vk` (:1216-1291), `_get_key_code_for_char` (:1293-1342), `_type_to_page` (:1144-1214).
**Signature:** `async _input_text_element_node_impl(element_node, text, clear=True, is_sensitive=False) -> dict | None` returning `{'input_x','input_y','actual_value'}`.

### Decisive source
```python
# Direct value assignment for compound/native inputs (date/time/color/range, jQuery datepickers):
#   -> native setter bypasses React's tracker, then dispatch focus/input/change/blur + jQuery
if self._requires_direct_value_assignment(element_node):
    await self._set_value_directly(...)   # returns input_coordinates

# Clear via 3 strategies: (1) JS value/contenteditable clear w/ native-setter + input/change events,
#   (2) triple-click+Delete, (3) Cmd/Ctrl+A + Backspace (platform-aware modifier)
# Focus via CDP DOM.focus, fallback click-to-focus
# Type char-by-char: keyDown(base_key,code,modifiers,vk) -> char(text) -> keyUp
#   contenteditable first-char drop bug: check document.activeElement.textContent after 1st char, retype if missing
# Readback actual_value (skip for sensitive)
# Auto-retry on concatenation mismatch: if clear requested and readback != text but is a
#   prefix/suffix of a longer value -> clear + set via native setter in one JS call
```

**Flow:** scroll into view (detached-node tolerant) → resolve objectId → occlusion-aware focus → direct-assignment check (date/time ⇒ set directly) → clear (3-strategy ladder) → char-by-char typing with proper key codes/modifiers → framework events (input/change/blur + React fiber + Vue) → readback → concatenation auto-retry.
**Invariant:** React controlled components need the **native prototype setter** (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set`) not the instance setter, else the input event is ignored; the setter is picked per element type (input vs textarea vs web-component — calling the HTMLInputElement setter on a textarea throws Illegal invocation); `is_sensitive` skips readback/logging; contenteditable first-char drop is detected and retyped.
**Probe:** `tests/ci/security/test_sensitive_data.py`, `tests/ci/test_variable_substitution.py`, `tests/ci/browser/test_dom_serializer.py` (typing fixtures).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_input_text_element_node_impl _clear_text_field _set_value_directly nativeInputValueSetter contenteditable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the React-native-setter bypass (the single most porting-critical invariant), the clear ladder, the char-by-char key-event grammar, and the concatenation auto-retry. Adapt the key-code tables to host.
