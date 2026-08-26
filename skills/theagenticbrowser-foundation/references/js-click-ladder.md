<!-- capsule-v2 -->
# JS-click degradation ladder — why does a browser agent click via page.evaluate instead of Playwright's element.click()?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When the trusted click path keeps failing on real-world pages, what is the fallback order and which special cases (select options, same-tab links, expanding menus) must be handled inside the click itself?

## attach-wait → scroll → JS click with option/link/menu special cases
**Path/Symbol:** `core/skills/click_using_selector.py`:`click` (`:17-59`), `do_click` (`:62-130`), `perform_javascript_click` (`:163-217`); `perform_playwright_click` retained but disabled at `:122-124`.
**Signature:** `async def click(selector, wait_before_execution: float = 0.0) -> str`.
**Data Shape:** Returns a string: success summary + outer HTML of the clicked target, OR menu-detected rewrite, OR "selector invalid — retrieve DOM again" error message. Errors are DATA (returned strings), never raised.

### Decisive source
```python
element = await asyncio.wait_for(
    page.wait_for_selector(selector, state="attached", timeout=2000), timeout=2000)
try:    await element.scroll_into_view_if_needed(timeout=200)
except Exception: pass                      # scroll failure is non-fatal
try:    await element.wait_for_element_state("visible", timeout=200)
except Exception: pass                      # invisibility is non-fatal too

if element_tag_name == "option":            # clicking an <option> selects it on the parent
    await parent_element.select_option(value=element_value)

#Playwright click seems to fail more often than not... just going with JS click
msg = await perform_javascript_click(page, selector)
```
Inside `perform_javascript_click`: `option` → set parent value + dispatch bubbling `change` Event; `a` → force `element.target = "_self"` so links never open tabs the agent can't see; any element → compare `aria-expanded` before/after and return "Very important: … a menu has appeared … Get all_fields DOM" when false→true.
**Flow:** optional pre-wait → wait attached (2 s) → best-effort scroll+visibility checks → option? select_option : JS click → mutation observer window wraps the whole thing.
**Invariant:** Failure semantics are inverted from normal code: a missing selector returns an actionable retry instruction ("Proceed by retrieving DOM again") instead of raising, because the consumer is an LLM that should re-fetch DOM state rather than crash the loop. The `aria-expanded` diff is what turns a plain click into menu-awareness without extra tool calls. Same-tab forcing exists because a background tab is invisible to `get_current_page()` (last-open-page heuristic) and would strand the agent.
**Probe:** No tests (coverage caveat). Graph pins: BA tool `click_tool` wrapper (`browser_agent.py:282-293`) is the sole production caller; `enter_text_and_click.py:66` reuses `do_click` for composite flows.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "javascript click selector aria-expanded", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the JS-click default with option/same-tab/menu special cases and error-as-data semantics. Adapt timeouts to your site latency. Omit the disabled native `perform_playwright_click` unless you have headless-trusted targets where real input events matter.
