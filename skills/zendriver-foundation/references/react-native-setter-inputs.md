<!-- capsule-v2 -->
# react-native-setter-inputs — why `.value = x` silently fails on React controlled inputs

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How must an automation library set input values so React's onChange actually fires?

## Native prototype setter keeps the tracker stale on purpose
**Path/Symbol:** `zendriver/core/element.py:Element.clear_input` (:701-715), `clear_input_by_deleting` (:717-759); direct tests `tests/core/test_react_controlled_input.py` + fixture `tests/sample_data/react-controlled-input-test.html`.
**Signature:** `await self.apply("(el) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, ''); el.dispatchEvent(new InputEvent('input', {...})); }")`.
**Data Shape:** JS source embedded in Python; both methods dispatch a bubbling `InputEvent` after mutating via the prototype setter.

### Decisive source
```python
# Use the native prototype setter instead of a direct element.value assignment.
# Direct assignment goes through React's instance-level tracker setter, updating
# trackerValue and the DOM simultaneously. The subsequent InputEvent then sees no
# mismatch and skips onChange. The native setter bypasses the tracker so React
# correctly fires onChange.
```
and in `clear_input_by_deleting`, per-iteration (:747-753):
```python
# Use native prototype setter to bypass React's _valueTracker.
# Direct assignment (n.value = x) goes through React's instance-level
# setter, ... — the subsequent InputEvent sees no mismatch and skips onChange.
nativeSetter.call(n, n.value.slice(0, -1));
n.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
```

**Flow:** delete-loop focuses the element, selects end-of-input, synthesizes Backspace keydown (keyCode 8 — chosen over Delete because VK_DELETE can be a backward-delete no-op on some VM environments, in-source comment :731-734), trims one char through `nativeSetter`, fires input event, awaits 50ms. The test fixture asserts React state transitions that only happen when the setter trick is used (the module docstring documents the pre-fix "mixed value" bug: old "10" + new "25" → "025").
**Invariant:** every programmatic value mutation MUST go through `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set` followed by an explicit bubbling input event; direct assignment makes React state diverge from DOM silently. This is framework-behavior-coupled, not CDP behavior.
**Probe:** direct tests: `tests/core/test_react_controlled_input.py::test_clear_input_does_not_notify_react` (:23), `::test_clear_input_by_deleting_does_not_notify_react` (:50), `::test_fill_react_controlled_input_produces_mixed_value` — all against `sample_file("react-controlled-input-test.html")`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "clear_input react native setter", limit: 5 });
```

## Verdict
Adopt verbatim for any React-targeting automation; re-verify against major React versions (tracker mechanism is internal); omit the Backspace-vs-Delete VM workaround if you control the target environment.
