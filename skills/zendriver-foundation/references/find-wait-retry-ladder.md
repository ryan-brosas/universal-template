<!-- capsule-v2 -->
# find-wait-retry-ladder — how do find/select/xpath turn "not found yet" into a bounded wait?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** What retry cadence, timeouts, and exception contracts distinguish the four finder entry points?

## Same loop skeleton, three different failure contracts
**Path/Symbol:** `zendriver/core/tab.py:find` (:191-243), `select` (:245-275), `find_all`/`select_all` (:277-340), `xpath` (:342-378), `wait_for` (:1154-1194).
**Signature:** `async def find(text, best_match=True, return_enclosing_element=True, timeout=10) -> Element`; `async def select(selector, timeout=10)`; `async def xpath(self, xpath: str, timeout: float = 2.5) -> List[Element]`.
**Data Shape:** all loop on `loop.time()` deltas with `await self.sleep(0.5)` between attempts; `Tab.sleep(t=0.25)` calls `update_target()` first, so every poll also refreshes target state.

### Decisive source
```python
# xpath: never raises, returns []
while (loop.time() - start_time) < timeout and len(items) == 0:
    try:
        await self.send(cdp.dom.enable(), True)
        items = await self.find_all(xpath, timeout=0)
    except Exception:
        items = []  # find_elements_by_text may raise exception
    await self.disable_dom_agent()
return items
```
vs `find`, which raises after the budget:
```python
if loop.time() - start_time > timeout:
    raise asyncio.TimeoutError(f"Timeout ({timeout}s) waiting for element with text: '{text}'")
```

**Flow:** text search (`find_elements_by_text`) fetches the full doc once (`get_document(-1, True)`), runs `dom.perform_search` + `get_search_results(0, nresult)`, discards the search, maps node ids through `util.filter_recurse`, promotes `node_type == 3` text nodes to their parent element (`elem.parent or elem`, :618-629), then sweeps iframes client-side for case-insensitive text matches (:637-661) and ends with `disable_dom_agent()`. `best_match` picks `min(items, key=lambda el: abs(len(text) - len(el.text_all)))` (:689-691).
**Invariant:** `xpath` swallows *all* exceptions and returns `[]`; `find`/`select`/`wait_for` raise `asyncio.TimeoutError`; `select_all`/`find_all` return possibly-empty lists without raising. Mixing these contracts (e.g. making xpath raise) breaks callers that use it as a probe.
**Probe:** direct tests pin all four: `tests/core/test_tab.py::test_find_finds_element_by_text` (:68), `::test_find_times_out_if_element_not_found` (:78), `::test_select` (:85), `::test_xpath` / `::test_xpath_no_results` (:189-202).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "xpath find_all retry", limit: 5 });
```

## Verdict
Adopt the loop skeleton and the raise-vs-return contract split verbatim; adapt poll interval (0.5s) and defaults (10s/2.5s) per app; keep DOM enable/disable bracketing — leaving DOM enabled leaks event traffic.
