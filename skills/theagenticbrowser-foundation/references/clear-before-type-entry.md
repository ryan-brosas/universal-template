<!-- capsule-v2 -->
# Clear-before-type text entry — why does every fill start by blanking the field, and which fill mode fires framework events?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you enter text into React/Vue-controlled inputs reliably, and what is the correct clear sequence when a field already holds a value?

## value-blank then keyboard.type; silent property-set as the non-event alternative
**Path/Symbol:** `core/skills/enter_text_using_selector.py`:`entertext` (`:84-160`), `do_entertext` (`:163-222`), `custom_fill_element` (`:41-82`), `bulk_enter_text` (`:225-263`), `EnterTextEntry` (`:19-38`).
**Signature:** `async def entertext(entry: EnterTextEntry) -> str`; `async def do_entertext(page, selector, text_to_enter, use_keyboard_fill=True)`; entry supports BOTH attribute and item access (`entry['query_selector']` via `__getitem__`).
**Data Shape:** `EnterTextEntry(query_selector, text)`. Returns two-tier dict (`summary_message`, `detailed_message` incl. element outer HTML). Bulk wraps per-entry results as `[{"query_selector": ..., "result": <str>}]` — never raises on individual failure.

### Decisive source
```python
# entertext() ALWAYS blanks before delegating:
await page.evaluate("""(selector) => { const el = document.querySelector(selector);
                        if (el) el.value = ''; }""", query_selector)
result = await do_entertext(page, query_selector, text_to_enter)   # use_keyboard_fill=True

# do_entertext keyboard path:
await elem.focus(); await press_key_combination("Control+A")
await press_key_combination("Backspace");
await page.keyboard.type(text_to_enter, delay=1)

# custom_fill_element (use_keyboard_fill=False): silent, no events
element.value = text_to_enter;   # docstring: does NOT trigger input/change events
```
The system prompt teaches the agent the SAME discipline as a multi-step fallback (`browser_agent.py:74-77`): empty string → Ctrl+A → Delete, then verify empty, then type.

**Flow:** highlight element → subscribe mutation observer → JS value-blank → keyboard fill (focus, Ctrl+A, Backspace, typed chars w/ 1 ms delay) or silent property set → refocus → unsubscribe after 100 ms drain → rewrite result if mutations appeared.
**Invariant:** The pre-blank is unconditional — entering into a non-empty field without clearing produces concatenated values on sites that don't reset on focus. Keyboard typing (not `fill`) is chosen so frameworks see real key events; the silent path exists for speed but its no-event caveat is documented in-source and the system prompt warns about it. Bulk is sequential (never parallel) because each entry can trigger page navigations/menus that invalidate later selectors.
**Probe:** No tests (coverage caveat). Graph pins: `trace_path --function-name entertext --direction inbound` shows `bulk_enter_text` and the BA tool wrapper; `press_key_combination` import ties the clear sequence to the same keyboard module the agent prompt describes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "entertext bulk keyboard fill", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt unconditional clear-before-type and the keyboard-vs-silent fill fork with its event caveat. Adapt the delay and the clear keystrokes to locale-specific inputs. Omit parallelization of bulk fills — sequential is the contract that keeps selectors valid.
