<!-- capsule-v2 -->
# ClickableElementDetector heuristic ladder — deciding interactivity without executing page JS

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** Which signals, in what priority order, mark a DOM node as interactive when all you have is AX tree + snapshot styles + attributes?

## is_interactive(): hard exclusions → strong positives → graded heuristics
**Path/Symbol:** `browser_use/dom/serializer/clickable_elements.py:ClickableElementDetector.is_interactive` (6-246).
**Signature:** `@staticmethod def is_interactive(node: EnhancedDOMTreeNode) -> bool`
**Data Shape:** consumes node_type, tag_name, attributes, ax_node (role/properties), snapshot_node (bounds/cursor_style), `has_js_click_listener` (CDP getEventListeners-derived flag).

### Decisive source
```python
# Check for JavaScript click event listeners detected via CDP (without DOM mutation)
# this handles vue.js @click, react onClick, angular (click), etc.
if node.has_js_click_listener: return True
# IFRAME elements should be interactive if they're large enough to potentially need scrolling
if ... == 'IFRAME' or ... 'FRAME':
    if width > 100 and height > 100: return True
if node.tag_name == 'label':
    if node.attributes and node.attributes.get('for'): return False   # avoid double-activating
    if has_form_control_descendant(node, max_depth=2): return True    # label > span > input
...
# aria disabled / hidden => False; focusable/editable/settable or
# checked/expanded/pressed/selected presence => True
...
interactive_tags = {'button','input','select','textarea','a','details','summary','option','optgroup'}
```

**Flow:** non-element/html/body excluded → JS-listener flag wins immediately → big iframes (>100x100) interactive → label with `for` EXCLUDED (proxying label would double-activate the external control — "can destroy the real clickable element on apartments.com"); wrapper labels/spans with a form control within depth 2 included → search-indicator class/id/data tokens → AX properties: disabled/hidden veto, focusable/editable/settable/checked/expanded/pressed/selected/required/autocomplete/keyshortcuts affirm → native interactive tags → onclick/tabindex attrs → role ∈ 16-role set → AX role ∈ same-family set → icon-sized (10-50px²) elements with any of {class,role,onclick,data-action,aria-label} → final fallback `cursor_style == 'pointer'`.
**Invariant:** order is load-bearing: vetoes (aria-disabled/hidden, label[for]) must fire before affirmative attribute checks. Size-0 elements stay eligible ("invisible clickable overlays") — visibility is CSS's job, not bbox size. The relaxed-size comment documents a deliberate prior-bug fix; SVG heuristics are deliberately commented out (decorative by default).
**Probe:** no direct unit file; deterministic pin: `grep -n "has_form_control_descendant\|apartments.com\|cursor_style == 'pointer'" browser_use/dom/serializer/clickable_elements.py` (:9, :138, :243). Coverage caveat: exercised only via integration serialization runs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "ClickableElementDetector is_interactive", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the veto-before-affirm ordering + wrapper-label depth-2 rule for any element detector; adapt the search-indicator vocabulary and role sets per locale/framework; omit cursor-style fallback if you lack computed-style access.
