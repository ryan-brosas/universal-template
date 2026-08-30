<!-- capsule-v2 -->
# Stale-node retry ladder — when a DOM query fails with "could not find node", how do you recover without an infinite loop?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you handle the DOM changing between when you grabbed an element and when you query it, without spinning forever on a stale document?

## One-retry stale-node recovery with an explicit last-attempt marker
**Path/Symbol:** `zendriver/core/tab.py:query_selector` (:514-571), `query_selector_all` (:408-512); `Element.update` (:276-319).
**Signature:** `Tab.query_selector(selector, _node=None) -> Element | None`; `query_selector_all(selector, _node=None, _include_frames=False)`.
**Data Shape:** on `ProtocolException` with message containing `"could not find node"`, the code distinguishes two cases: (a) a user-supplied `_node` went stale → `await _node.update()` (re-resolve by backend_node_id) then retry; (b) the top-level document went stale → refetch `get_document` then retry. A `__last` attribute on the node marks the retry as the final attempt.

### Decisive source
```python
except ProtocolException as e:
    if _node is not None and "could not find node" in e.message.lower():
        if getattr(_node, "__last", None):
            delattr(_node, "__last"); return None        # already retried once — give up
        if isinstance(_node, element.Element):
            await _node.update()                          # re-resolve by backend_node_id
        setattr(_node, "__last", True)
        return await self.query_selector(selector, _node) # exactly ONE retry
    elif "could not find node" in e.message.lower() and doc:
        doc = await self.send(cdp.dom.get_document(-1, True))   # stale top doc
        setattr(doc, "__last", True)
        return await self.query_selector(selector, doc)
```

**Flow:** every query is a `get_document` (or uses the passed node) → `DOM.querySelector` → `filter_recurse` the returned id back to a node in the tree → wrap as Element. If the node id no longer resolves, the element is re-`update()`d (fresh `get_document` + `resolve_node` by backend id) and retried ONCE; a second failure returns `None`/`[]` rather than recursing forever. The `__last` marker is deleted on the successful path so the element stays reusable.
**Invariant:** retry is bounded to ONE (marker-guarded), and recovery is by **backend_node_id** (stable across DOM churn) not node_id (volatile). The `disable_dom_agent` on the error path (:564) suppresses the noisy `DOM.disable` exception so it doesn't mask the real error. Cross-reference: linkedin-scrapers' playwright-resilient-helpers and selenium-click-finder-ladder — the "element went stale mid-interaction" problem is universal across the suite.
**Probe:** REAL tests — `tests/core/test_tab.py:95 test_query_selector_all_include_frames_queries_nested_iframe_documents` (monkeypatched `send` proves the iframe-document traversal and stale-node handling via `__last`), plus `test_select`/`test_find` live. Deterministic pin (anchored at the `zendriver/` package dir): `grep -n '__last' core/tab.py` → :470-488,:543-561.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "query_selector __last could not find node update", limit: 5 });
```

## Verdict
Adopt: bounded one-retry stale-node recovery keyed on backend_node_id with an explicit last-attempt marker; re-resolve elements before re-querying. Adapt the retry count to your DOM churn rate (1 is conservative and safe). Omit the `_include_frames` traversal unless you need cross-iframe queries. Coverage: test-pinned (iframe traversal) + source-pinned (retry ladder).
