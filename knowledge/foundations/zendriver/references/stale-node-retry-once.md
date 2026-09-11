<!-- capsule-v2 -->
# stale-node-retry-once — how do query_selector calls survive a DOM that changed under them?

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** What exactly happens on ProtocolException "could not find node", and why the `__last` attribute?

## One refresh-and-retry, then give up — enforced by a sentinel attribute
**Path/Symbol:** `zendriver/core/tab.py:Tab.query_selector_all` (:408-512) and `query_selector` (:514-571).
**Signature:** `async def query_selector_all(self, selector: str, _node: cdp.dom.Node | Element | None = None, _include_frames: bool = False) -> List[Element]`.
**Data Shape:** sentinel `__last` set on the *node object itself* (a CDP dom.Node or Element); iframe content docs collected via explicit stack walk when `_include_frames`.

### Decisive source
```python
except ProtocolException as e:
    if _node is not None:
        if e.message is not None and "could not find node" in e.message.lower():
            if getattr(_node, "__last", None):
                delattr(_node, "__last")
                return []          # second failure with a stale node → empty, not infinite
            if isinstance(_node, element.Element):
                await _node.update()   # refresh the element against a fresh doc
            setattr(_node, "__last", True)
            return await self.query_selector_all(selector, _node, _include_frames=_include_frames)
    else:
        if ... "could not find node" in e.message.lower():
            # The document node is stale; refetch and retry once
            doc = await self.send(cdp.dom.get_document(-1, True))
            setattr(doc, "__last", True)
            return await self.query_selector_all(selector, doc, ...)
    await self.disable_dom_agent()
    raise
```

**Flow:** normal path queries `dom.query_selector_all(doc.node_id, selector)` and maps ids to Elements via `filter_recurse` over the already-fetched tree (Elements carry the shared `doc` for cheap `.parent`/`.children`). On stale-node errors: for an Element arg, update it and retry once; for the implicit document, refetch the doc and retry once; the `__last` sentinel guarantees the retry is the *last* attempt (second failure returns `[]`/`None` and clears the sentinel). Any other ProtocolException disables the DOM agent and re-raises.
**Invariant:** recursion depth is bounded at one extra attempt per call — the comment *"make sure this isn't turned into infinite loop"* is load-bearing. Ports that retry unconditionally on stale-node errors will spin forever on pages that mutate every tick.
**Probe:** direct tests pin include-frames querying and nested-iframe traversal (`tests/core/test_tab.py::test_query_selector_all_include_frames_queries_nested_iframe_documents`, :95); static anchors at pin: `setattr(_node, "__last", True)` → :478,:551; `setattr(doc, "__last", True)` → :487,:561.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "query_selector_all could not find node", limit: 5 });
```

## Verdict
Adopt the retry-once-with-sentinel pattern for any cache-keyed remote lookup; adapt error-string matching to your protocol's exact codes; omit the frames branch if you never query cross-document.
