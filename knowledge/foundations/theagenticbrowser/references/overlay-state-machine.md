<!-- capsule-v2 -->
# Overlay state machine — how does collapsed/expanded × init/processing/done state survive DOM rewrites and user clicks?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When porting an injected page-side agent UI, how do you model view mode (collapsed pill vs expanded chat) and progress state so that clicks, Python pushes, and full-page navigations all agree on ONE current state without a store?

## Two-axis state, class-carried, DOM-derived on read
**Path/Symbol:** `core/utils/ui/injectOverlay.js:updateOverlayState` (:406-454), `showCollapsedOverlay` (:356-404), `showExpandedOverlay` (:522-579); python mirror `core/utils/ui_manager.py:overlay_processing_state` (:28).
**Signature:** `updateOverlayState(processing_state, is_collapsed)`; `showCollapsedOverlay(processing_state = "processing")`; `showExpandedOverlay(processing_state = "init", show_steps = true)`.
**Data Shape:** `processing_state ∈ {"init","processing","done"}` (string enum, default `"init"`); `is_collapsed` bool. No JS-side state object exists — the CURRENT state is read back out of the DOM by sniffing classes.

### Decisive source
```javascript
// injectOverlay.js :406-421 — one writer wipes ALL six state classes first
function updateOverlayState(processing_state, is_collapsed) {
  const element = is_collapsed
    ? document.getElementById("tawebagent-overlay")
    : document.getElementById("tawebagentExpandedAnimation");
  if (!element) return;
  // Remove all state classes
  element.classList.remove(
    "tawebagent-init", "tawebagent-processing", "tawebagent-done",
    "tawebagent-initStateLine", "tawebagent-processingLine", "tawebagent-doneStateLine"
  );
```
```javascript
// :389-399 — collapsed click RE-DERIVES state from DOM before expanding
collapsed.addEventListener("click", () => {
  const state = document.getElementById("tawebagent-overlay")
      .querySelector(".tawebagent-processing") ? "processing"
    : document.getElementById("tawebagent-overlay")
      .querySelector(".tawebagent-done") ? "done" : "init";
  showExpandedOverlay(state, show_details);
});
```

**Flow:** write path = `removeOverlay()` → rebuild chosen view → `window.overlay_state_changed(isCollapsed)` notify → `updateOverlayState(state, isCollapsed)` strips six classes then adds exactly one (`tawebagent-{state}` collapsed / `tawebagent-{state}StateLine` expanded, where expanded target is the 2px progress bar `#tawebagentExpandedAnimation`, NOT the container). Same switch also drives input gating: `processing` ⇒ `disableOverlay()` (placeholder "Processing...", textarea disabled), `init|done` ⇒ `enableOverlay()`. Read path = click handlers never consult a variable; they querySelector the state class off the live element.
**Invariant:** (1) State lives in exactly one element's class list; any transition must strip all six classes or stale states accumulate. (2) Collapsed↔expanded transitions PRESERVE processing state by re-deriving it from the DOM before switching views — dropping this round-trip resets a running task's indicator to "init". (3) Python mirrors only `{overlay_is_collapsed, overlay_processing_state}` (`ui_manager.py:26-28`) and pushes via `updateOverlayState('<state>', <bool>)` evaluate — the two sides reconcile because BOTH derive from the same DOM after each injection.

**Probe:** `cd $REFERENCE_ROOT/TheAgenticBrowser && grep -c 'getElementById("tawebagent-overlay")' core/utils/ui/injectOverlay.js` → `3` (two read sites in the collapsed click ternary chain + one write site at :367); `grep -A7 'element.classList.remove' core/utils/ui/injectOverlay.js | grep -c 'tawebagent-'` → `6`. No test suite ships (repo-wide); these are deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "updateOverlayState collapsed expanded state class", limit: 4 });
// rank-1: injectOverlay.updateOverlayFunction core/utils/ui/injectOverlay.js 406-454
```

## Verdict
Adopt the two-axis model (view-mode × progress-state), single-writer strip-then-add class discipline, and DOM-as-source-of-truth re-derivation on view switches — it is what makes the UI crash-safe under arbitrary navigation. Adapt the class names/z-index (2147483646 = max−1) and the Python string-mirror if you have a real store (then keep the strip-first rule as a render invariant). Omit the typo'd function name family (`injectOveralyStyles`) and the dead `show_details` second parameter of `showCollapsedOverlay` (:356 accepts it, body ignores it). Coverage caveat: no upstream tests; behavior pinned by line-exact greps above.
