<!-- capsule-v2 -->
# Email Palette & Inline-CSS Constraint — why brand colors are duplicated, not shared

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you keep email chrome consistent with a web dashboard when email clients strip stylesheets?

## Convention-synced token twins; inline CSS strings only
**Path/Symbol:** `packages/python/awaithumans/server/channels/email/templates/palette.py` — constraint docstring (:1-15), `_BRAND/_BG_DARK/_TEXT_LIGHT` (:24-26), `LIGHT_PALETTE` (:30-36), `DARK_PALETTE` (:40+); consumers in `templates/renderers.py` (notification_html :40-76).
**Signature:** dataclass-based palette entries rendered as INLINE style strings at template time.
**Data Shape:** two palettes by surface: LIGHT for notification email, DARK for confirm/completed pages; brand tokens `_BRAND="#00E676"`, `_BG_DARK="#0A0A0A"`, `_TEXT_LIGHT="#F5F5F5"` mirror dashboard `globals.css @theme`.

### Decisive source
```python
# - Email clients (Gmail, Outlook) strip <style> blocks, so colors have
#   to appear as inline CSS strings at render time. No var(--foo).
# - Brand tokens duplicate the dashboard's @theme tokens. Keep them in
#   sync **by convention**, not by code-sharing — the consumption patterns
#   (inline CSS strings here vs CSS custom props there) are different
#   enough that sharing would be awkward.
```

**Flow:** renderer picks palette by surface → interpolates hex values directly into element style attributes → survives Gmail/Outlook sanitization.
**Invariant:** NO CSS variables reach email HTML; sync with dashboard theme is a documented human responsibility (`by convention`) because the abstraction cost of sharing outweighs drift risk at this scale.
**Probe:** `packages/python/tests/email/test_renderer.py` (`test_payload_html_escaped`:199 pins escaping in rendered HTML; palette assertions via renderers suite) — email suites green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "LIGHT_PALETTE DARK_PALETTE notification_html renderers palette", limit: 5 });
```
(rank-3 on the dashboard_static query resolves notification_html line-exact; palette module itself is constants-shaped — search_code/grep is the reliable primitive here.)

## Verdict
Adopt the inline-only rule and the convention-sync decision WITH its rationale comment; adapt tokens to your brand; omit the dark-surface twin only if you have single-surface emails.
