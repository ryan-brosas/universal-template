<!-- capsule-v2 -->
# JSON-LD @graph unpacking — why nine of twelve walkers silently scored zero on every WordPress site

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How must JSON-LD be enumerated so Yoast/RankMath `{"@context","@graph":[...]}` blocks yield their schemas?

## Shared BFS iterator preserving document order
**Path/Symbol:** `src/geo_optimizer/core/citability.py:_iter_jsonld_objects` (187–222).
**Signature:** `_iter_jsonld_objects(soup) -> Iterator[dict]`.
**Data Shape:** accepts `<script type="application/ld+json">` containing an object, an ARRAY of objects, or an object with `@graph`; malformed JSON is skipped (never raised); non-dict items dropped.

### Decisive source
```python
for script in soup.find_all("script", type="application/ld+json"):
    try:
        data = json.loads(script.string or "")
    except (json.JSONDecodeError, TypeError):
        continue
    queue = list(data) if isinstance(data, list) else [data]
    while queue:
        item = queue.pop(0)
        if not isinstance(item, dict):
            continue
        graph = item.get("@graph")
        if isinstance(graph, list):
            # Prepend so the graph's own members keep document order ahead of
            # whatever follows this container.
            queue = list(graph) + queue
            continue
        yield item
```

**Flow:** fix #326 patched THREE of TWELVE call sites; gap #4.16.3 found the other NINE reading only top-level keys — so on the Yoast/RankMath default single-block emission, Organization/WebSite/Article and their `sameAs` were invisible and every dependent detector scored zero. The shared helper replaced all sites; `schema_injector.analyze_html_file` got its own identical unpack (#schema-analyze gap).
**Invariant:** A porter who iterates `soup.find_all(...)` and `json.loads` each script WITHOUT array-and-graph flattening ships a detector that works on hand-written test pages and fails on most real CMS output. The prepend-BFS detail matters: appending would reorder nested members behind unrelated later scripts, changing "first schema wins" semantics downstream. Nested `@graph` inside `@graph` also unwinds because each yielded dict re-enters the loop check.
**Probe:** `tests/test_citability.py::TestContentFreshness::test_json_ld_recente` (+ `tests/test_core.py` FAQ/schema detection tests exercising @graph fixtures; `PYTHONPATH=src pytest tests/test_citability.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "@graph JSON-LD iter", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the flatten-everything iterator as THE way to enumerate structured data in any page analyzer; adapt to also accept RDFa/Microdata if needed; omit nothing — this one generalizes verbatim.
