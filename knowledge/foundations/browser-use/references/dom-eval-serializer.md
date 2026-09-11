<!-- capsule-v2 -->
# DOM eval serializer — ultra-concise tree for LLM query writing with truncation guards

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does an agent serialize a DOM tree into a compact, LLM-friendly form that preserves structure without blowing the context window?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/dom/serializer/eval_serializer.py` (480 lines): `DOMEvalSerializer` (:112) — `serialize_tree` (:116-233), `_serialize_children` (:236-300), `_build_compact_attributes` (:303-334), `_has_direct_text` (:337-344), `_get_inline_text` (:347-360), `_serialize_iframe` (:363-408), `_serialize_document_node` (:411-480); constants `EVAL_KEY_ATTRIBUTES` (:13), `SEMANTIC_ELEMENTS` (:51), `COLLAPSIBLE_CONTAINERS` (:89), `SVG_ELEMENTS` (:92).
**Signature:** `serialize_tree(node, include_attributes, depth=0) -> str`.

### Decisive source
```python
# Only interactive elements get [i_X] index notation; non-interactive show just the tag
# Invisible elements are skipped UNLESS they're containers (html/body/div/main/section/...)
#   or iframes (which might have visible children)
# SVG: show <svg> tag + interactive index, collapse children to a comment; skip SVG child elements
# Truncation guards in _serialize_children:
#   - list (ul/ol): skip li after 50, emit "... (N more items ... use evaluate to get more)"
#   - consecutive <a>: skip after 50, emit "... (N more links ...)"
# Inline text replaces children for non-containers (compact); containers always recurse
# EVAL_KEY_ATTRIBUTES deliberately EXCLUDES id and class to force robust structural selectors
#   (id/class can have special chars like '+' that break CSS queries)
```

**Flow:** walk the simplified tree; skip excluded/invisible nodes (recurse into children); emit compact `<tag attr="val">` lines with `[i_X]` for interactive, `scroll="..."` for scrollables, inline text for leaves; recurse containers; truncate long lists/link-runs with an explicit "use evaluate to get more" hint; serialize iframe content documents permissively (cross-origin: assume visible when no snapshot).
**Invariant:** the output is a single flat indented string (self-closing tags only, no closing tags) sized for LLM context; id/class are deliberately omitted to force structural selectors; truncation is explicit and tells the agent how to get more; iframe content uses a permissive visibility rule (no snapshot ⇒ assume visible).
**Probe:** `tests/ci/browser/test_dom_serializer.py`, `tests/ci/test_dom_paint_order_serialization.py`, `tests/ci/test_ax_name_matching.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "DOMEvalSerializer serialize_tree EVAL_KEY_ATTRIBUTES truncation SVG iframe-content", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the compact self-closing-tag grammar, the interactive-only `[i_X]` indexing, the id/class exclusion for structural selectors, and the explicit truncation-with-hint guards. Adapt to host's node model.
