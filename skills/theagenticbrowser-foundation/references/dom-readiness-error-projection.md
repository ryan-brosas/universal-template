<!-- capsule-v2 -->
# DOM readiness gate + error-target projection — how do you gate every DOM read on load state and describe a failed action's target back to the LLM without blowing context?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0 — source-available; SaaS-competing-use restricted) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** Where does a browser agent enforce "DOM is readable" before extracting, and what should it tell the model when a click/type action misses its target?

## The two-function DOM-helper plane (uncited before pass 4)
**Path/Symbol:** `core/utils/dom_helper.py`:`wait_for_non_loading_dom_state` (:9-18), `get_element_outer_html` (:21-45). Callers: readiness gate ← `get_dom_texts_func`/`get_dom_field_func` (`get_dom_with_content_type.py:47/:79`) and BA tools `get_dom_text`/`get_dom_fields`; outer-HTML projection ← `click`+`do_click` (`click_using_selector.py`), `entertext`+`do_entertext` (`enter_text_using_selector.py`), `enter_text_and_click`. Graph evidence: `search_graph file_pattern=*dom_helper*` (in=2 each), two inbound traces.
**Signature:** `async def wait_for_non_loading_dom_state(page: Page, max_wait_millis: int)`; `async def get_element_outer_html(element: ElementHandle, page: Page, element_tag_name: str|None = None) -> str`.
**Data Shape:** Gate input = page + millisecond budget; NO return value — expiry is silent. Projection input = element handle + optional pre-known tag name (skips one evaluate roundtrip); output = opening tag string only, never closing tag or children.

### Decisive source
```python
# dom_helper.py :9-18 — soft gate: deadline expiry is SILENT
while asyncio.get_event_loop().time() < end_time:
    dom_state = await page.evaluate("document.readyState")
    if dom_state != "loading":
        break
    await asyncio.sleep(0.05)
# dom_helper.py :35-43 — allowlisted attribute projection
attributes_of_interest: list[str] = ['id', 'name', 'aria-label', 'placeholder', 'href', 'src', 'aria-autocomplete', 'role', 'type',
                                     'data-testid', 'value', 'selected', 'aria-labelledby', 'aria-describedby', 'aria-haspopup']
opening_tag: str = f'<{tag_name}'
for attr in attributes_of_interest:
    value: str = await element.get_attribute(attr)
    if value:
        opening_tag += f' {attr}="{value}"'
```

**Flow:** skill resolves page → `wait_for_non_loading_dom_state(page, 2000)` polls `document.readyState` every 50 ms until not `"loading"` OR budget elapses (loop just ends; caller proceeds regardless) → read/projection proceeds. On action failure, click/type skills build `f"Element not found with selector: {selector}"` plus `await get_element_outer_html(...)` so the critique/model sees a compact re-description of what WAS at that spot.
**Invariant:** The readiness gate is best-effort BY DESIGN — it must never raise on timeout, because the repo treats timeouts as soft failures everywhere. The projection is an ALLOWLIST (15 attributes), not `outerHTML` — bounded payload keeps error messages inside the token budget; adding attributes is a context-budget decision.
**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -c "attributes_of_interest" core/utils/dom_helper.py` → `2` (decl + use); `grep -n "readyState" core/utils/dom_helper.py` → exactly `:13`; `grep -rn "wait_for_non_loading_dom_state" --include='*.py' core | grep -v "def \|dom_helper"` → 4 call sites (`get_dom_with_content_type.py:9,47,79` import+2 uses). Coverage caveat: repo ships no tests; deterministic line-pinned greps at pin `71daa28`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "wait_for_non_loading_dom_state get_element_outer_html readyState", limit: 10 });
```

## Verdict
Adopt both contracts verbatim: silent-expiry readiness polling before ANY DOM extraction, and allowlisted opening-tag projection as the error-context payload for failed actions (this is how the agent self-corrects without re-shooting the whole DOM). Adapt the poll cadence/budget per host and the allowlist per target sites; consider excluding `value` from the projection on credential-bearing pages (it can echo typed secrets into LLM context/error logs). Omit nothing structural. Caveat: no upstream tests; graph coverage `no_recorded_issue` for this path at generation `2026-08-23T00:02:33Z`.
