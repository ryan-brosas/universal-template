<!-- capsule-v2 -->
# CDP input-dispatch primitives — how do you synthesize trusted mouse/key/wheel/file input over raw DevTools, and when does each escape hatch fire?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What exact Input/DOM-domain event sequences make clicks, typing, shortcuts, wheel scrolls, and file uploads behave like real user input — and where does synthetic input silently diverge from it?

## Raw Input-domain dispatch family + BH_DEBUG_CLICKS overlay
**Path/Symbol:** `src/browser_harness/helpers.py:click_at_xy/type_text/press_key/scroll` (:152-238), `dispatch_key/upload_file` (:480-496), `_KEYS` table (:216-223).
**Signature:** `click_at_xy(x, y, button="left", clicks=1)`; `type_text(text)`; `press_key(key, modifiers=0)`; `scroll(x, y, dy=-300, dx=0)`; `dispatch_key(selector, key="Enter", event="keypress")`; `upload_file(selector, path)`.
**Data Shape:** modifiers bitfield 1=Alt, 2=Ctrl, 4=Meta(Cmd), 8=Shift. `_KEYS` maps special keys to `(windowsVirtualKeyCode, code, text)` triples (e.g. Enter→(13,"Enter","\r")); unknown single chars fall back to `ord(key[0])`.

### Decisive source
```python
shortcut_modifiers = modifiers & (1 | 2 | 4)  # Alt/Ctrl/Meta turn single keys into shortcuts.
printable_char = len(key) == 1 and bool(text) and not shortcut_modifiers
cdp("Input.dispatchKeyEvent", type="keyDown", **base, **({} if printable_char or not text else {"text": text}))
if printable_char:
    cdp("Input.dispatchKeyEvent", type="char", text=text, **{k: v for k, v in base.items() if k != "text"})
cdp("Input.dispatchKeyEvent", type="keyUp", **base)
```

**Flow:** click = two `Input.dispatchMouseEvent` calls (`mousePressed` then `mouseReleased`, same x/y/button/clickCount — no move events); type = one `Input.insertText` (fast but bypasses framework listeners); key = `keyDown` → optional `char` → `keyUp`; wheel = a single `mouseWheel` mouse-event carrying deltaX/deltaY; DOM-level fallback `dispatch_key` focuses the element and fires a synthetic `KeyboardEvent(key, code, keyCode, which, bubbles)` when a site listens for DOM events rather than trusted input; upload resolves nodeId via `DOM.getDocument(depth=-1)` + `DOM.querySelector`, fails loud on miss, then `DOM.setFileInputFiles` with `[path]` or `list(path)`.
**Invariant:** The `char` event is emitted ONLY for printable single chars with NO Alt/Ctrl/Meta held (`modifiers & 7 == 0`). With Ctrl/Cmd held, emitting `char` makes Chrome treat the chord as a printable letter instead of a shortcut — this is why fill_input's select-all dispatches `rawKeyDown` directly instead of calling press_key. Special keys must carry their virtual key codes or listeners reading `e.keyCode` never fire.
**Probe:** Executed against pinned source: patched `cdp` recorder shows `press_key('a')` → `[keyDown, char, keyUp]` while `press_key('a', modifiers=2)` → `[keyDown, keyUp]` (char exactly once). Direct tests: `tests/unit/test_helpers.py:113-146` pins select-all's platform-correct modifier (Cmd=4 darwin / Ctrl=2 else), forbids the `char`-with-text='a' event, and requires Backspace via keyDown; :149-165 pins clear_first=False skipping Ctrl-A. click_at_xy/scroll/upload_file have NO direct unit test — coverage caveat; behavior anchored at source :171-172, :237-238, :491-496.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", name_pattern: "^(click_at_xy|type_text|press_key|dispatch_key|scroll|upload_file)$", file_pattern: "*.py", fields: ["lines", "signature"] });
```

## Verdict
Adopt the pressed/released pair with matching clickCount, the char-gating rule, virtual-key-code table for special keys, and fail-loud setFileInputFiles ladder. Adapt the BH_DEBUG_CLICKS debug overlay (env-gated, never-raise PIL crosshair at DPR scale written into `ipc._TMP/debug_click_<n>.png` before the real dispatch) to your own artifact dir. Omit PIL import inside the hot path if your host lacks it — the try/except guarantees the real click still fires.
