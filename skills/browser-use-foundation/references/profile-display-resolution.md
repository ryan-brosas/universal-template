<!-- capsule-v2 -->
# Display/viewport resolution FSM — how should headless vs headful decide viewport, window size, and scale?

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** Given user-supplied (or missing) viewport/window/screen prefs and an optional physical display, what is the deterministic resolution order that can never produce headless+no_viewport?

## detect_display_configuration(): preference ladder ending in contradiction asserts
**Path/Symbol:** `browser_use/browser/profile.py:BrowserProfile.detect_display_configuration` (1235-1288); helpers `get_display_size` (@cache, 236-262), `get_window_adjustments` (265); called from `model_post_init` (833).
**Signature:** `def detect_display_configuration(self) -> None`
**Data Shape:** mutates `screen`, `headless`, `viewport`, `window_position`, `window_size`, `no_viewport`, `device_scale_factor` in place; `get_display_size` cached across the process (first call wins).

### Decisive source
```python
self.screen = self.screen or display_size or ViewportSize(width=1920, height=1080)
if self.headless is None:
    self.headless = not has_screen_available
if self.headless:
    # Headless mode: always use viewport for content size control
    self.viewport = self.viewport or self.window_size or self.screen
    self.window_position = None; self.window_size = None; self.no_viewport = False
else:
    self.window_size = self.window_size or self.screen
    if user_provided_viewport: self.no_viewport = False
    else: self.no_viewport = True if self.no_viewport is None else self.no_viewport
...
if self.no_viewport:
    self.viewport = None; self.device_scale_factor = None; self.screen = None
assert not (self.headless and self.no_viewport), 'headless=True and no_viewport=True cannot both be set'
```

**Flow:** resolve screen (user > OS display > 1920x1080 fallback) → default headless from display availability → HEADLESS branch: viewport = user > window_size > screen; window geometry nulled; no_viewport forced False → HEADFUL branch: window_size defaults to screen; explicit user viewport enables viewport mode, otherwise content-fits-window (no_viewport=True) → device_scale_factor forces viewport mode when set → finalize: no_viewport wipes viewport/dsf/screen entirely; viewport mode backfills dsf=1.0 → final asserts.
**Invariant:** `headless=True ⇒ no_viewport=False and viewport is not None` — headless rendering has no window to fit, so a viewport MUST exist or every screenshot/DOM measurement degrades. The wipe-to-None in the no_viewport branch is deliberate (stale screen values would leak into CDP calls). Porters who "simplify" by always setting a viewport break real headful window-fitting behavior.
**Probe:** deterministic (executed green in gate 5): with mocked 2560x1440 display → `BrowserProfile()` gets headless=False, window 2560, no_viewport=True, viewport=None; with display None → forced headless + viewport set; explicit `viewport=` respected in headful with no_viewport=False. Coverage caveat: no upstream unit file pins this method.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "detect_display_configuration get_display_size", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-branch resolution order and terminal invariant for any browser/screen config layer; adapt the OS-probing helpers (`AppKit`/`screeninfo`) per platform; omit the window-adjustment pixel constants unless matching mac/win title bars matters.
