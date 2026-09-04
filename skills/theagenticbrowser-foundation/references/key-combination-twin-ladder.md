<!-- capsule-v2 -->
# Key-combination ladder twins — how does a '+' key grammar map onto Playwright's down/press/up, and why do the agent tool and the composite helper diverge?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0 — source-available; SaaS-competing-use restricted) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How should keyboard shortcuts be executed so modifier order is preserved, side effects are detected, and both agent-facing and internal callers get the right failure shape?

## press_key_combination tool twin vs do_ composite twin
**Path/Symbol:** `core/skills/press_key_combination.py`:`press_key_combination` (:14-66, agent tool; in=2 from graph), `do_press_key_combination` (:69-110, composite helper). Inbound callers of the module (trace_path): `browser_agent.press_key_combination_tool` (hop 1), `enter_text_and_click` + `do_entertext`/`entertext` (hop 2 — the Enter-on-search-field rule rides this file).
**Signature:** `async def press_key_combination(key_combination: Annotated[str, "The key to press, e.g., Enter, PageDown etc"]) -> str`; `async def do_press_key_combination(browser_manager: PlaywrightManager, page: Page, key_combination: str) -> bool`.
**Data Shape:** Input grammar = `'+'`-separated tokens; ALL tokens except the last are modifiers (`keys[:-1]`), the last is pressed. Tool twin returns protocol strings and RAISES `ValueError('No active page found. OpenURL command opens a new page.')` on no page; composite twin returns bare bool and takes page as a parameter.

### Decisive source
```python
# :41-63 — hold modifiers, press last, release, THEN drain the observer window
keys = key_combination.split('+')
dom_changes_detected=None
def detect_dom_changes(changes:str):
    nonlocal dom_changes_detected
    dom_changes_detected = changes
subscribe(detect_dom_changes)
for key in keys[:-1]:  # All keys except the last one are considered modifier keys
    await page.keyboard.down(key)
await page.keyboard.press(keys[-1])
for key in keys[:-1]:
    await page.keyboard.up(key)
await asyncio.sleep(0.1) # sleep for 100ms to allow the mutation observer to detect changes
unsubscribe(detect_dom_changes)
if dom_changes_detected:
    return f"Key {key_combination} executed successfully.\n As a consequence of this action, new elements have appeared in view:{dom_changes_detected}. This means that the action is not yet executed and needs further interaction. Get all_fields DOM to complete the interaction."
return f"Key {key_combination} executed successfully"
```

**Flow (tool twin):** resolve singleton → get_current_page → None ⇒ raise ValueError → subscribe mutation callback → down(modifiers…) → press(last) → up(modifiers…) → sleep 100 ms → unsubscribe → success string, rewritten into "Get all_fields DOM" guidance when the observer fired. **Flow (composite twin):** try/except wrapper → `inspect.currentframe().f_code.co_name` names the screenshot bracket (`do_press_key_combination_start`/`_end`) → same down/press/up ladder → exceptions log + `return False`, success `return True`.
**Invariant:** Modifiers are HELD (`keyboard.down`) not pressed, and released only AFTER the final key — pressing "Control" then "C" as two presses is a different event stream and breaks e.g. Ctrl+A select-all inside clear-before-type. The observer subscription must wrap the keystrokes and drain ≥100 ms before unsubscribe, or side-effect menus appear without feedback. The twins intentionally diverge: tool = error-as-data strings + exception on missing page; composite = bool + screenshot evidence, NO observer window (the composing skill owns feedback).
**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -c "keyboard.down\|keyboard.up" core/skills/press_key_combination.py` → `4` (down+up per twin); `grep -n "keys\[:-1\]" core/skills/press_key_combination.py` → `:50,:57,:94,:101` (twice per twin); `grep -n "currentframe().f_code.co_name" core/skills/press_key_combination.py` → `:88`. Coverage caveat: repo ships no tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "press_key_combination keyboard down press up subscribe", limit: 10 });
```

## Verdict
Adopt the down→press→up modifier grammar and the subscribe/drain/unsubscribe wrapping verbatim; adopt the twin split (agent-facing protocol strings vs internal bool) when you have composite skills that must NOT double-report feedback. Adapt the 100 ms drain to your observer latency and rename success strings to your own next-action vocabulary (keep the "success BUT re-fetch DOM" semantics). Omit the `inspect.currentframe()` naming if your screenshot harness passes explicit labels. Caveat: no upstream tests; graph coverage `no_recorded_issue` at generation `2026-08-23T00:02:33Z`.
