<!-- capsule-v2 -->
# Highlight-then-act UX contract — how does an action skill mark its target, and why must decoration failures never fail the action?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you give a human observer visual feedback about which element the agent is acting on, without making that feedback part of the critical path?

## Fail-open class-toggle highlight + start/end screenshot brackets around every skill action
**Path/Symbol:** `core/browser_manager.py`:`PlaywrightManager.highlight_element` (`:424-442`); `take_screenshots` (`:515-540`); consumers `enter_text_using_selector.py:128` and `click_using_selector.py` (`highlight_element(selector, True)`).
**Signature:** `async def highlight_element(self, selector: str, add_highlight: bool)` / `async def take_screenshots(self, name: str, page: Page|None, full_page: bool = True, include_timestamp: bool = True, load_state: str = 'domcontentloaded', take_snapshot_timeout: int = 15*1000)`.
**Data Shape:** Highlight = CSS class `tawebagent-ui-automation-highlight` (fading/pulsating border) toggled via `eval_on_selector`. Screenshot naming = `f"{int(time.time_ns())}_{name}.png"` inside `_screenshots_dir`.

### Decisive source
```python
# :429-442 — self-removing class + swallow-everything except handler
await page.eval_on_selector(selector, '''e => {
            let originalBorderStyle = e.style.border;
            e.classList.add('tawebagent-ui-automation-highlight');
            e.addEventListener('animationend', () => {
                e.classList.remove('tawebagent-ui-automation-highlight')
            });}''')
...
except Exception:
    # This is not significant enough to fail the operation
    pass

# :532-537 — screenshot failure returns None instead of raising
try:
    await page.wait_for_load_state(state=load_state, timeout=take_snapshot_timeout)
    await page.screenshot(path=screenshot_path, full_page=full_page,
                        timeout=take_snapshot_timeout, caret="initial", scale="device")
    return screenshot_path
except Exception as e:
    logger.error(f"Failed to take screenshot ...")
    return None
```
**Flow:** `entertext` calls `highlight_element(query_selector, True)` BEFORE mutating (:128) → class added; `animationend` removes it automatically (one pulse per action) → action runs between `take_screenshots(f"{function_name}_start", page)` and `_end` calls → both screenshots and highlights are observability-only. The removal path (`add_highlight=False`) exists for explicit cleanup. Note `originalBorderStyle` is captured but never restored — the class's animation IS the restore mechanism.
**Invariant:** Decoration is never on the critical path: a missing element, detached frame, or CSP issue in `eval_on_selector` silently passes, and screenshot failures return None (callers pass the value onward without checking — e.g. orchestrator logs "SS Saved to Path: None" rather than crashing). `caret="initial"` prevents a blinking caret in captures; `scale="device"` captures at device pixel ratio. Skills call `PlaywrightManager()` fresh each time but the singleton guarantees one browser.
**Probe:** `grep -c "tawebagent-ui-automation-highlight" core/browser_manager.py` → `5` (:428 + :437 are COMMENTS carrying the name; :431 add, :433 remove-by-animation, :438 explicit remove); `grep -n "not significant enough to fail" core/browser_manager.py` → `441`; `grep -c "caret=" core/browser_manager.py` → `1`; `grep -n "highlight_element(query_selector, True)" core/skills/enter_text_using_selector.py` → `128`. Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "highlight_element eval_on_selector animationend screenshot", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: fail-open decoration with self-removing animation class and None-returning screenshots bracketed start/end. Adapt: class name/colors to your overlay theme. Omit: nothing load-bearing. Coverage caveat: no upstream tests; probes line-pinned at pin `71daa28`.
