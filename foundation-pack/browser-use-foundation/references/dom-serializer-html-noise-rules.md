<!-- capsule-v2 -->
# HTML serializer noise pruning + table thead synthesis — reconstructing clean HTML (incl. shadow DOM) for markdown conversion

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** How do you turn an enhanced DOM tree (with shadow roots and iframe documents) into HTML that downstream markdownify can consume without SPA state blobs polluting it?

## serialize(): declarative-shadow-DOM reconstruction with targeted skip rules
**Path/Symbol:** `browser_use/dom/serializer/html_serializer.py:HTMLSerializer.serialize` (27-170), `_serialize_table_children` (172-246), `_serialize_attributes` (248-276).
**Signature:** `def __init__(self, extract_links: bool = False)` / `def serialize(self, node: EnhancedDOMTreeNode, depth: int = 0) -> str`
**Data Shape:** in: EnhancedDOMTreeNode; out: HTML string. Shadow roots render as `<template shadowrootmode="...">`; iframe content documents inline; href dropped unless extract_links; data-* always dropped.

### Decisive source
```python
# Skip code tags with display:none - these often contain JSON state for SPAs
if tag_name == 'code' and node.attributes:
    style = node.attributes.get('style', '')
    if 'display:none' in style.replace(' ', '') or 'display: none' in style: return ''
    # Also check for bpr-guid IDs (LinkedIn's JSON data pattern)
    element_id = node.attributes.get('id', '')
    if 'bpr-guid' in element_id or 'data' in element_id or 'state' in element_id: return ''
if tag_name == 'img' and src.startswith('data:image/'): return ''   # tracking pixels
...
# Serialize shadow roots FIRST (for declarative shadow DOM)
for shadow_root in node.shadow_roots: ...
# Then serialize light DOM children (for slot projection)
for child in node.children: ...
```

**Flow:** DOCUMENT → children; DOCUMENT_FRAGMENT (shadow root) → `<template shadowroot=...>` wrapper; ELEMENT → skip set {style, script, head, meta, link, title} + the code/display:none + bpr-guid/data/state-id + base64-img rules → void elements self-close → TABLE: if no thead but first tr has th cells, synthesize `<thead>` around it and `<tbody>` around remaining rows (markdownify needs proper tables); emit colgroup/caption before the synthesized head → IFRAME: inline content_document children → else shadow roots FIRST then light-DOM children → TEXT escaped (&, <, > only), attributes value-escaped (+quotes).
**Invariant:** shadow roots serialize BEFORE light children so declarative shadow DOM parses correctly; the thead-synthesis triggers ONLY when no existing thead and the FIRST tr carries th cells — otherwise structure passes through untouched (idempotent for already-normal tables). Attribute pruning (href, data-*) is unconditional per flag, not content-aware.
**Probe:** deterministic source pins: `grep -n "shadowrootmode\|bpr-guid\|_serialize_table_children" browser_use/dom/serializer/html_serializer.py` (:52 note: attribute spelled `shadowroot` at :52, docstring says shadowrootmode; :81; :172). Coverage caveat: consumed by markdown_extractor tests (`tests/ci/test_markdown_extractor.py`) indirectly; no direct unit file.
**Retrieve note:** graph anchor under `browser-use.browser_use.dom.serializer.html_serializer`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "HTMLSerializer _serialize_table_children", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the skip-rule list + shadow-first ordering as a battle-tested noise filter for page-to-markdown pipelines; adapt site-specific id patterns (bpr-guid is LinkedIn-flavored) to your targets; omit table synthesis if your markdown converter handles headerless tables.
