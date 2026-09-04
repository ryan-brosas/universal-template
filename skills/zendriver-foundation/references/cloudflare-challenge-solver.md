<!-- capsule-v2 -->
# cloudflare-challenge-solver — shadow-DOM challenge discovery and the 15%-from-left click policy

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How does zendriver find the Turnstile widget inside closed shadow roots, and where exactly does it click?

## find → wait-visible → geometry → click loop with success heuristics
**Path/Symbol:** `zendriver/core/cloudflare.py:cf_find_interactive_challenge` (:17-68), `cf_wait_for_interactive_challenge` (:71-104), `verify_cf` (:126-269).
**Signature:** `async def cf_find_interactive_challenge(tab) -> tuple[Element | None, Element | None, Element | None]`; `async def verify_cf(tab, click_delay=5, timeout=15, challenge_selector=None, flash_corners=False)`.
**Data Shape:** detection needle is the substring `"challenges.cloudflare.com"` inside a shadow root's HTML; visibility check rejects `"display: none"` in the iframe's style attr.

### Decisive source
```python
shadow_host_nodes = util.filter_recurse_all(
    doc, lambda n: hasattr(n, "shadow_roots") and bool(n.shadow_roots))
for host_node in shadow_host_nodes:
    for shadow_root_node in host_node.shadow_roots:
        shadow_root_element = Element(shadow_root_node, tab, shadow_root_node)
        html_content = await shadow_root_element.get_html()
        if "challenges.cloudflare.com" in html_content:
```
and the click-point policy (:179-189):
```python
x_coords = content_quad[0::2]
y_coords = content_quad[1::2]
min_x, max_x, min_y, max_y = min(x_coords), max(x_coords), min(y_coords), max(y_coords)
click_x = min_x + (max_x - min_x) * 0.15
click_y = min_y + (max_y - min_y) / 2
```

**Flow:** full-doc fetch (`get_document(-1, True)` — shadow roots included) → scan hosts for shadow roots whose serialized HTML contains the challenges host → locate the inner iframe element → poll until visible (0.5s cadence, default 5s budget) → box-model from `dom.get_box_model(node_id)` (content quad) → click at 15% width / 50% height of the *iframe*, repeated every `click_delay` seconds until the response input disappears or gains a value (`check_input` :231-246); "could not find position" after ≥1 click is treated as SUCCESS (widget vanished = solved, :262-265). Input lookup ladder: custom selector → `input[name=cf-turnstile-response]` → `input[name=cf_challenge_response]`.
**Invariant:** success is inferred, not confirmed — the loop exits on disappearance/value, so a port must keep both heuristics or it will click forever on solved widgets. Clicking targets the iframe geometry, NOT the input element (which lives in a closed document).
**Probe:** static anchors at pin: `grep -n 'click_x = min_x' zendriver/core/cloudflare.py` → :188; `grep -n 'input\[name=cf-turnstile-response\]' zendriver/core/cloudflare.py` → :209 (priority comment) and :218 (code site); no dedicated unit suite (network/challenge-bound) — coverage caveat stated.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "verify_cf cloudflare challenge", limit: 5 });
```

## Verdict
Adopt the discovery scan + geometry math; adapt click coordinates only with measured data (15%/50% encodes Turnstile's checkbox placement); omit entirely unless solving challenges is your use case.
