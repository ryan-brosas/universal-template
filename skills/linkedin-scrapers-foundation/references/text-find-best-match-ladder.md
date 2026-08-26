<!-- capsule-v2 -->
# Text-find ladder — how do you find an element "by text" over CDP (no XPath engine), and why does find() double as a wait?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you implement Selenium-style `find_element(by text)` on top of raw CDP, where matches arrive as useless TEXT NODES and scripts count as text — and how do the retry loops turn finders into wait conditions?

## Poll loop + DOM.perform_search + text-node→parent hop + best-match-by-length
**Path/Symbol:** `zendriver/core/tab.py:find` (:191-243), `select` (:245-275), `find_all` (:277-304), `select_all` (:306-340), `xpath` (:342-378) — poll wrappers; `Tab.find_elements_by_text` (:573-663) — the real search; `Tab.find_element_by_text` (:665-703) — best-match picker; `Tab.disable_dom_agent` (:165-180).
**Signature:** `Tab.find(text, best_match=True, return_enclosing_element=True, timeout=10) -> Element`; `Tab.xpath(xpath, timeout=2.5) -> List[Element]` (**never raises** — returns `[]`); `Tab.wait_for(selector=None, text=None, timeout=10)`; `await tab(text=…, selector=…)` is an alias of `wait_for`.
**Data Shape:** search = `cdp.dom.perform_search(text, True)` → `(search_id, nresult)` → `get_search_results(search_id, 0, nresult)` → **must** `discard_search_results(search_id)`; hits are node ids resolved against the already-fetched doc tree by `util.filter_recurse(doc, lambda n: n.node_id == nid)`; misses fall back to `dom.resolve_node(node_id=nid)` (skip on ProtocolException).

### Decisive source
```python
# find_elements_by_text: server-side search, then resolve hits against the LOCAL tree
search_id, nresult = await self.send(cdp.dom.perform_search(text, True))
node_ids = await self.send(cdp.dom.get_search_results(search_id, 0, nresult)) if nresult else []
await self.send(cdp.dom.discard_search_results(search_id))     # free the server-side result set
for nid in node_ids:
    node = util.filter_recurse(doc, lambda n: n.node_id == nid)  # local tree lookup first
    if not node:
        node = await self.send(cdp.dom.resolve_node(node_id=nid))  # fallback for detached hits
    ...
    if elem.node_type == 3:            # TEXT NODE: useless for clicking
        if not elem.parent:
            await elem.update()        # make sure parent edge exists before trusting .parent
        items.append(elem.parent or elem)   # hop to enclosing element; text node as last resort

# find(): every finder is also a waiter — same shape in select/find_all/select_all/xpath
start_time = loop.time()
while True:
    item = await self.find_element_by_text(text, best_match, return_enclosing_element)
    if item:
        return item
    if loop.time() - start_time > timeout:
        raise asyncio.TimeoutError(f"Timeout ({timeout}s) waiting for element with text: '{text}'")
    await self.sleep(0.5)

# find_element_by_text best_match: closest text LENGTH to the query wins
if best_match:
    closest_by_length = min(items, key=lambda el: abs(len(text) - len(el.text_all)))
```

**Flow:** CDP has no "find by visible text"; zendriver uses the DevTools **server-side** `DOM.perform_search` (which searches the live document including iframes/shadow content), then re-resolves each returned node id inside the client-side tree snapshot fetched once via `get_document(-1, True)` — local-tree resolution avoids a round-trip per hit. Because `<p>text</p>` yields the *text node*, not the `<p>`, every type-3 hit hops to `.parent` (updating the node first if the parent edge is missing), so callers always get a clickable element. The four public finders (`find/find_all/select/select_all`) wrap the primitive in a 0.5s-poll loop that raises `asyncio.TimeoutError` at `timeout` — which is exactly what makes `await tab.find("Login")` usable as a wait condition. `best_match=True` disambiguates needle-in-haystack queries ("login" matches thousands of scripts/headings) by returning the element whose text length is CLOSEST to the query length — the login button, not a script tag containing "login". `xpath()` differs deliberately: enable-DOM → reuse `find_all` with timeout=0 in a bounded while, swallow ALL exceptions to `[]`, and `disable_dom_agent()` after each attempt — it never raises, only returns possibly-empty results. After every search pass, `disable_dom_agent()` sends `DOM.disable` and **swallows ProtocolException**, because "agent not enabled" (-32000) is not a real error but masking it would otherwise hide genuine failures ("could not find node") from callers' logs.
**Invariant:** (1) ALWAYS `discard_search_results` — the server pins the result set until told otherwise (leak per call). (2) A found text node must be converted to its parent BEFORE returning; returning the text node hands the caller something `click()` can't use. (3) The retry loops must check elapsed time BEFORE sleeping again and must raise TimeoutError (except `xpath`, contractually never-raise). (4) `DOM.disable` exceptions are noise to be ignored at debug level, never propagated.
**Probe:** REAL tests — `tests/core/test_tab.py`: `test_find_finds_element_by_text` (:68-75, `tab.find("Apples")` → `tag == "li"` and `text == "Apples"`), `test_find_times_out_if_element_not_found` (:78-82, missing text raises `asyncio.TimeoutError` within timeout=1), `test_select` (:85-92), `test_query_selector_all_include_frames_queries_nested_iframe_documents` (:95+, monkeypatched node trees prove iframe traversal), `test_xpath` (:189)/`test_xpath_no_results` (:202). Live-bot pin: `tests/bot_detection/test_browserscan.py:13-19` asserts `find_element_by_text("Test Results:")` resolves through `.parent.children[-1]` to the value element on a real bot-detection page.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "find_elements_by_text perform_search best_match discard_search_results", limit: 5 });
```

## Verdict
Adopt: server-side text search + local-tree id resolution + text-node→parent hop + elapsed-time poll loop as THE portable recipe for text-finding without a browser driver's built-ins; best-match-by-length as the cheap disambiguator for noisy pages. Adapt the 0.5s poll interval and timeout defaults per surface. Coverage: directly test-pinned (test_tab.py find/select/xpath families + live browserscan bot test).
