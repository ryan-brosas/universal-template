<!-- capsule-v2 -->
# is_actually_scrollable CSS gate — why CDP's scrollable flag alone lies, and the overflow allowlist that fixes it

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** How do you decide an element is scrollable for LLM scroll-hint purposes when CDP misses iframes and dynamically-sized containers?

## CDP flag → rect comparison → computed-style overflow allowlist
**Path/Symbol:** `browser_use/dom/views.py:EnhancedDOMTreeNode.is_actually_scrollable` (624-672), `should_show_scroll_info` (674-700), `scroll_info` (719-788), `get_scroll_info_text` (790-824).
**Signature:** `@property def is_actually_scrollable(self) -> bool`
**Data Shape:** consumes `snapshot_node.scrollRects/clientRects/computed_styles` (DOMSnapshot plane); output feeds `scroll_info` percentages/pages and the serializer's `[scroll: N.N↑ M.M↓ P%]` hints.

### Decisive source
```python
has_vertical_scroll = scroll_rects.height > client_rects.height + 1  # +1 for rounding
has_horizontal_scroll = scroll_rects.width > client_rects.width + 1
if has_vertical_scroll or has_horizontal_scroll:
    if self.snapshot_node.computed_styles:
        overflow = styles.get('overflow', 'visible').lower()
        overflow_x = styles.get('overflow-x', overflow).lower()
        overflow_y = styles.get('overflow-y', overflow).lower()
        # Only allow scrolling if overflow is explicitly set to auto, scroll, or overlay
        # Do NOT consider 'visible' overflow as scrollable - this was causing the issue
        allows_scroll = (overflow in ['auto','scroll','overlay']
            or overflow_x in ['auto','scroll','overlay'] or overflow_y in ['auto','scroll','overlay'])
```

**Flow:** trust `is_scrollable` from CDP first → else compare scroll vs client rects (+1px rounding slack) → require explicit CSS overflow ∈ {auto, scroll, overlay} on either axis; WITHOUT style info, fall back to a conservative common-container tag set {div, main, section, article, aside, body, html} → `should_show_scroll_info` suppresses nested-scroll spam (parent already scrollable ⇒ False) but ALWAYS shows for `<iframe>` (Chrome's iframe scrollHeight=0 detection hole) and body/html.
**Invariant:** overflowing content with default `overflow: visible` is NOT scrollable — content merely clipped; treating visible as scrollable was a real bug ("this was causing the issue"). The +1px slack prevents float-rounding false positives. Iframe elements bypass every gate (always show scroll info) because Chrome under-reports iframe scrollability. Porting only the rect comparison without the CSS gate floods the LLM with unusable scroll hints.
**Probe:** no direct upstream unit file; deterministic pin: `grep -n "Do NOT consider 'visible' overflow" browser_use/dom/views.py` (:658) + `'scroll' in ...` allowlist (:660-663); iframe special case `should_show_scroll_info` returns True at :685-686. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "is_actually_scrollable should_show_scroll_info scroll_info", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-gate ladder (CDP flag → geometry → explicit overflow allowlist) for any scroll-hint UI; adapt the conservative tag fallback to your DOM; omit the pages-above/below formatting if your consumers take raw numbers.
