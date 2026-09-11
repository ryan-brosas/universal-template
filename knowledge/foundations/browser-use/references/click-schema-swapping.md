<!-- capsule-v2 -->
# Click re-registration + coordinate gating — how does one `click` action switch between index-only and index+coordinates schemas at runtime?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you expose different tool schemas per model capability without duplicating action implementations?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `_register_click_action` (:2126), `set_coordinate_clicking` (:2204), stored handlers `self._click_by_index` (:826) / `self._click_by_coordinate` (:790), new-tab detection `_detect_new_tab_opened` (:682).
**Signature:** `def _register_click_action(self) -> None`; `def set_coordinate_clicking(self, enabled: bool) -> None`.

### Decisive source
```python
def _register_click_action(self) -> None:
    # Remove existing click action if present
    if 'click' in self.registry.registry.actions:
        del self.registry.registry.actions['click']
    if self._coordinate_clicking_enabled:
        @self.registry.action('Click element by index or coordinates...', param_model=ClickElementAction)
        async def click(params, browser_session):
            if params.index is not None:  return await self._click_by_index(params, browser_session)
            else:                          return await self._click_by_coordinate(params, browser_session)
    else:
        @self.registry.action('Click element by index.', param_model=ClickElementActionIndexOnly)
        async def click(params, browser_session):
            return await self._click_by_index(params, browser_session)

def set_coordinate_clicking(self, enabled):
    if enabled == self._coordinate_clicking_enabled: return   # idempotent guard
    self._coordinate_clicking_enabled = enabled
    self._register_click_action()
```
```python
# New-tab side effect shared by BOTH click paths:
async def _detect_new_tab_opened(browser_session, tabs_before) -> str:
    await asyncio.sleep(0.05)   # let CDP Target.attachedToTarget propagate
    new_tabs = [t for t in await browser_session.get_tabs() if t.target_id not in tabs_before]
    if new_tabs:
        try: dispatch SwitchTabEvent; return '. Automatically switched to new tab ...'
        except Exception: return '. Note: This opened a new tab (...) - switch to it if you need to interact'
```

**Flow:** handlers are defined once inside `__init__` and stored on self → schema selection is a DELETE-then-re-register of the single `click` entry with either param model → `set_coordinate_clicking` no-ops when unchanged → click-by-index asserts index != 0 (index 0 reserved for "no interactive elements"), looks the node up fresh from the selector map (stale index ⇒ soft refresh message, not error), and on `<select>` validation errors falls through to `dropdown_options` as a helpful shortcut.
**Invariant:** re-registration must delete the old entry first or the registry keeps the stale schema; the idempotence check prevents churn; tab-set diffing must capture `tabs_before` BEFORE the click event or newly-opened tabs are undetectable.
**Probe:** `tests/ci/test_coordinate_clicking.py` — default disabled + index-only schema (:16/:22/:30), enable/disable round-trip (:42/:66), `test_set_coordinate_clicking_idempotent` (:78), schema-title consistency (:92), model-detection patterns (:143).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "_register_click_action set_coordinate_clicking ClickElementActionIndexOnly _detect_new_tab_opened", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt delete-and-reregister schema swapping over a stable handler pair plus the tabs-before/tabs-after new-tab adoption; adapt which models get coordinates; omit vendor-specific model lists.
