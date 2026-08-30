<!-- capsule-v2 -->
# Thread title scraping — how is the nearest h1 to #isso-thread found without XPath?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What is the exact DOM walk order and attribute override chain for deriving a thread's title/id?

## parse.thread
**Path/Symbol:** `isso/utils/parse.py:thread` (lines 9–70).
**Signature:** `thread(data, default="Untitled.", id=None) -> (id, title)`.
**Data Shape:** input = raw page bytes; html5lib DOM tree; anchor = div/section with id="isso-thread".

### Decisive source
```python
el = list(filter(
    lambda i: i.attributes["id"].value == "isso-thread",
    filter(lambda i: "id" in i.attributes,
           chain(*map(html.getElementsByTagName, ("div", "section")))),
))
...
try:
    id = unquote(el.attributes["data-isso-id"].value)
except (KeyError, AttributeError):
    pass
try:
    return id, unquote(el.attributes["data-title"].value)
except (KeyError, AttributeError):
    pass

while el is not None:  # el.parentNode is None in the very end
    visited.append(el)
    rv = recurse(el)
    if rv:
        return id, "".join(gettext(rv)).strip()
    el = el.parentNode
```

**Flow:** locate the embed anchor (div/section only) → `data-title` wins outright → else walk UPWARD from the anchor; at each level depth-first search for the first H1 (visited-set prevents re-descending) → concatenate its text nodes → fallback `(id, "Untitled.")`.
**Invariant:** Search is ANCESTORS-THEN-UP (nearest enclosing container's heading), not document-order — a porter using querySelector('h1') would pick a DIFFERENT title on multi-article pages. `data-isso-id` can override the URI used as thread key (title-fetch-on-create consumes this).
**Probe:** `grep -c data-title isso/utils/parse.py` (`1`); anchor marker `grep -c '"isso-thread"' isso/utils/parse.py` (`1`).
**Test:** `isso/tests/test_utils.py:test_thread` (fixture HTML matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "parse thread h1 isso-thread recurse gettext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt upward-nearest-heading heuristics for widget-embedded title discovery. Adapt tag names. Keep the visited-set — it's what makes the walk terminate and stay deterministic.
