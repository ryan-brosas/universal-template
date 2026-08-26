<!-- capsule-v2 -->
# viewport-css-pixel-contract — which coordinate space do Input events use, and when must device pixels be divided out?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How are viewport overrides pinned so coordinate clicks stay valid across a session?

## CSS-pixel coordinate contract
**Path/Symbol:** `skills/cdp/interaction-skills/viewport.md` whole doc — read viewport (:5–23), force size (:25–42), mobile emulation (:44–58), w=0 target trap (:60–62), Traps (:64–69).
**Signature:** read: evaluate `{w: innerWidth, h: innerHeight, sx: scrollX, sy: scrollY, pw, ph, dpr: devicePixelRatio}`; pin: `Emulation.setDeviceMetricsOverride({width, height, deviceScaleFactor, mobile})`; clear: `Emulation.clearDeviceMetricsOverride()`.
**Data Shape:** innerWidth/innerHeight = CSS-pixel viewport (what Input.* consumes); captureScreenshot output dimensions = CSS × devicePixelRatio. Override PERSISTS across navigations within the session — clear before handing the browser back. Mobile emulation = setDeviceMetricsOverride + setTouchEmulationEnabled + Network.setUserAgentOverride together.

### Decisive source
```md
- **`captureScreenshot` returns device pixels, not CSS pixels.** If
  `devicePixelRatio = 2` and you eyeball an element at (400, 300) in the
  screenshot, click at (200, 150) in CSS pixels.
...
- **Responsive sites that use `matchMedia` at page load** may not re-evaluate
  breakpoints after override. Apply `setDeviceMetricsOverride` **before**
  `Page.navigate`, not after.
```

**Flow:** pin override BEFORE navigate (matchMedia-at-load sites never re-evaluate) → all coordinates now stable in the pinned space → wait ~300ms post-override for resize-debounced sites → re-read getBoundingClientRect after ANY resize → clear override at session end.
**Invariant:** The unit contract is absolute: Input.* = CSS pixels; screenshots = device pixels; the division happens exactly once at read-off time. `innerWidth` evaluating to 0 means you attached to a NON-WINDOW surface (omnibox popup/DevTools target) — a target-routing problem (listPageTargets + session.use), not a viewport problem.
**Probe:** `grep -cF 'innerWidth' skills/cdp/interaction-skills/viewport.md` → 3; `grep -cF 'devicePixelRatio' <same>` → 3; `grep -cF 'setDeviceMetricsOverride' <same>` → 5; `grep -cF 'persists across navigations' <same>` → 1; `grep -cF '**before** \`Page.navigate\`' <same>` → 1.
**Retrieve:** search_graph --project browser-harness-js --query "setDeviceMetricsOverride" resolves the generated.ts wrapper line-exact.

## Verdict
Adopt pin-before-navigate + CSS/device-pixel discipline as hard rules; adapt DPR handling per host hardware. Omit touch emulation unless driving mobile layouts.
