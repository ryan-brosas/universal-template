<!-- capsule-v2 -->
# React controlled-input silent-failure — why does `el.value = x` silently not work on React inputs, and what two setters fix it?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you clear/type into a React-controlled input so React's `onChange` actually fires, given React's `_valueTracker` intercepts direct value assignment?

## Native prototype setter bypass + InputEvent dispatch
**Path/Symbol:** `zendriver/core/element.py:clear_input` (:701-715), `clear_input_by_deleting` (:717-759).
**Signature:** `Element.clear_input()`; `Element.clear_input_by_deleting()` (Backspace-per-char variant).
**Data Shape:** the JS runs `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, '')` then `el.dispatchEvent(new InputEvent('input', {bubbles:true, cancelable:true}))`.

### Decisive source
```python
# clear_input:
(el) => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, '');
    el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
}
# clear_input_by_deleting inner loop:
const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
while (n.value.length > 0) {
    n.setSelectionRange(len, len);          // cursor to END; Backspace from end is reliable
    n.dispatchEvent(new KeyboardEvent("keydown", {key:"Backspace", code:"Backspace", keyCode:8, which:8, bubbles:true, cancelable:true}));
    nativeSetter.call(n, n.value.slice(0, -1));  // native setter leaves trackerValue STALE
    n.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
    await new Promise((r) => setTimeout(r, d));  // d=50ms
}
```

**Flow:** React installs an instance-level `value` setter (`_valueTracker`) on controlled inputs. Direct `el.value = x` goes through it, updating both the DOM and `trackerValue` simultaneously; the subsequent `input` event then finds `el.value === trackerValue` and React concludes "nothing changed" → `onChange` never fires → the DOM silently reverts to the controlled value on React's next render (the "mixed value" bug: old "10" + typed "25" → "025"/"1025"). The native prototype setter BYPASSES the instance tracker, leaving `trackerValue` stale, so React correctly fires `onChange`. `clear_input_by_deleting` additionally dispatches a real Backspace keydown before each slice and uses `setSelectionRange(len,len)` because Backspace-from-end is more reliable than Delete-at-0 (which can be a no-op on some VMs → infinite loop).
**Invariant:** you must BOTH bypass the instance setter AND dispatch a real `input` event — either alone is insufficient (the event without the native setter still sees matching values; the setter without the event never notifies React). This is the exact same class of bug the browser-harness-js lane's react-controlled-input-writers capsule documents (HTMLInputElement.prototype value setter bypass + bubbling input Event).
**Probe:** REAL tests — `tests/core/test_react_controlled_input.py` (3 tests): `test_clear_input_does_not_notify_react`, `test_clear_input_by_deleting_does_not_notify_react`, `test_fill_react_controlled_input_produces_mixed_value` — each asserts React state becomes `""` after clear (would fail with "10" on regression) and that typing "25" yields exactly "25" not a mixed value.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "clear_input nativeSetter _valueTracker InputEvent", limit: 5 });
```

## Verdict
Adopt: native-prototype-setter + InputEvent pattern for React-controlled inputs; Backspace-from-end with per-char delay for the deleting variant. Adapt the delay to your form's re-render latency. Omit nothing — this is the canonical fix. Coverage: directly test-pinned (3 live tests, real Chromium).
