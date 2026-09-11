<!-- capsule-v2 -->
# Framework-aware input fill — why does raw CDP typing leave React/Vue inputs stale, and how do you fix it?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** `Input.insertText` bypasses framework listeners — how does a helper type into a controlled input so the framework sees it?

## focus → raw select-all → backspace → per-char key events → synthetic input/change
**Path/Symbol:** `src/browser_harness/helpers.py:fill_input` (:177-214) with `press_key` (:224-235) and `type_text` (:174-175).
**Signature:** `fill_input(selector, text, clear_first=True, timeout=0.0)`; raises RuntimeError when the element is missing.
**Data Shape:** `timeout>0` waits for late-rendered elements via `wait_for_element` before typing; `clear_first` sends select-all then Backspace.

### Decisive source
```python
if clear_first:
    # Dispatch select-all DIRECTLY — NOT via press_key, which always emits a
    # `char` event for single-char keys. With Ctrl/Cmd held, that `char`
    # makes Chrome treat the input as a printable "a" instead of firing the
    # select-all shortcut, leaving the field uncleared.
    mods = 4 if sys.platform == "darwin" else 2      # Cmd on macOS, Ctrl elsewhere
    select_all = {"key": "a", "code": "KeyA", "modifiers": mods,
                  "windowsVirtualKeyCode": 65, "nativeVirtualKeyCode": 65}
    cdp("Input.dispatchKeyEvent", type="rawKeyDown", **select_all)
    cdp("Input.dispatchKeyEvent", type="keyUp", **select_all)
    press_key("Backspace")
for ch in text:
    press_key(ch)
js(f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(!e)return;"
   f"e.dispatchEvent(new Event('input',{{bubbles:true}}));"
   f"e.dispatchEvent(new Event('change',{{bubbles:true}}));}})();")
```

**Flow:** focus via JS → (clear) raw select-all + Backspace → per-character `press_key` (real keyDown/char/keyUp with virtual key codes) → synthetic `input`+`change` events so the framework re-renders.
**Invariant:** the select-all must go through `rawKeyDown`/`keyUp`, NOT `press_key`, because `press_key` emits a `char` event for single-char keys that turns Ctrl/Cmd+A into a printable "a". `press_key` itself only fires `char` for printable chars WITHOUT Alt/Ctrl/Meta (modifier+key = shortcut, no char).
**Probe:** `tests/unit/test_helpers.py:82` `test_fill_input_focuses_types_and_fires_events`, `:104` raises-when-not-found, `:113` `test_fill_input_clear_first_sends_select_all_then_backspace`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "fill_input select all rawKeyDown framework input change", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the whole helper — the rawKeyDown-vs-press_key distinction is the load-bearing invariant; adapt modifier mapping per-OS; omit nothing. Directly test-pinned.
