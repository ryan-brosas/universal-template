<!-- capsule-v2 -->
# Cloudflare shadow-DOM checkbox solver — how do you detect a CF challenge living inside shadow roots and click its checkbox at a non-center point?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you find and click the Cloudflare Turnstile checkbox when the whole challenge is hidden in a closed shadow root, and why click at 15% width instead of center?

## Shadow-root signature scan + geometry click + success-by-disappearance
**Path/Symbol:** `zendriver/core/cloudflare.py:cf_find_interactive_challenge` (:17-68), `cf_wait_for_interactive_challenge` (:71-104), `verify_cf` (:126-269); wired as `Tab.verify_cf` (:1509-1532).
**Signature:** `cf_find_interactive_challenge(tab) -> (host_elem, shadow_root_elem, iframe_elem | None)`; `verify_cf(tab, click_delay=5, timeout=15, challenge_selector=None, flash_corners=False)`.
**Data Shape:** challenge signature = `"challenges.cloudflare.com"` appearing in the shadow-root's and iframe's outer HTML. `cf_wait_for_interactive_challenge` polls every 0.5s up to `timeout`, returning only when the iframe is visible (`"display: none" not in style`).

### Decisive source
```python
shadow_host_nodes = util.filter_recurse_all(doc, lambda n: hasattr(n, "shadow_roots") and bool(n.shadow_roots))
for host_node in shadow_host_nodes:
    for shadow_root_node in host_node.shadow_roots:
        if "challenges.cloudflare.com" in await shadow_root_element.get_html():
            for child_element in shadow_root_element.children:
                if "challenges.cloudflare.com" in await child_element.get_html():
                    return host_element, shadow_root_element, challenge_iframe
# click geometry — NOT center:
click_x = min_x + (max_x - min_x) * 0.15
click_y = min_y + (max_y - min_y) / 2
```

**Flow:** `cf_find_interactive_challenge` walks the DOM for every shadow-host node, checks each shadow root's HTML for the CF marker, then descends to the child iframe carrying the marker. `verify_cf` scrolls the iframe into view, reads its content-quad box model, computes the click point at **15% from the left edge, vertical center** (the actual Turnstile checkbox is left-aligned inside the frame, NOT centered — center-click misses it), then clicks via `tab.mouse_click`. Success is detected by the input **disappearing or gaining a value** (`check_input` loop), with a `"could not find position"` exception after a click treated as success (checkbox vanished). Selector priority: caller override → `input[name=cf-turnstile-response]` → `input[name=cf_challenge_response]`.
**Invariant:** the whole challenge is inside a CLOSED shadow root — a plain `query_selector` on the top document will never find it; you must enumerate shadow hosts and read their shadow-root HTML. And success is inferred from the challenge INPUT's disappearance, not from any page signal — the frame is cross-origin-isolated so you cannot inspect its internals directly.
**Probe:** no upstream unit test (needs live CF) — coverage caveat. Deterministic pins (anchored at the `zendriver/` package dir): `grep -n 'challenges.cloudflare.com' core/cloudflare.py` → :55,:59; `grep -n '\* 0.15' core/cloudflare.py` → :188; `grep -n 'cf-turnstile-response' core/cloudflare.py` → :209,:218. Cross-reference: growchief's `_isProxyUnavailable`/bot.tools.ts CF handling (AGPL, same lane) and linkedin-scrapers' browser-fingerprint-stealth — this is the concrete "solve the interstitial" primitive.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "cf_find_interactive_challenge shadow_roots verify_cf", limit: 5 });
```

## Verdict
Adopt: shadow-host enumeration + marker-in-HTML detection + off-center (15%/50%) checkbox click + success-by-disappearance. Adapt the marker string and click fraction to current CF DOM (re-verify; CF changes layouts). Omit the flash_corners debug overlay. Coverage: source-pinned only (no live-CF runner upstream).
