<!-- capsule-v2 -->
# Overlay lifecycle defects ledger — which five latent bugs in the Python↔overlay plane must a porter consciously fix or consciously keep?

**Source:** TheAgenticBrowser TheAgentic Community License 1.0 `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** Before porting the overlay/UI-manager pair, what is the verified list of shipped-but-wrong behaviors (state inversion, ghost calls, swallowed pushes, unguarded HTML, leaks) that silently corrupt ports when copied as-is?

## Five adjudicated defects, each with its exact site and the failure it causes
**Path/Symbol:** `core/utils/ui_manager.py` :83 (flag inversion), :119-120 (blanket swallow), :239-240 (ghost evaluate); `core/utils/ui/injectOverlay.js` :783 (innerHTML sink), :578 (uncleared interval).
**Signature:** n/a — this capsule is a defect census with evidence, not a single callable.

### Decisive source
```python
# ui_manager.py :79-83 — show_overlay EXPANDS but writes collapsed=True
async def show_overlay(self, page: Page):
    if not self.overlay_is_collapsed:
        logger.debug("Overlay is already expanded, ignoring show_overlay call")
        return
    await page.evaluate("showExpandedOverlay();")
    self.overlay_is_collapsed = True   # BUG: just expanded; mirror now lies
```
```python
# ui_manager.py :116-120 — state push failures vanish at debug level; no retry,
# no queue: until the next navigation reinjection, page and Python disagree
try:
    js_bool = str(self.overlay_is_collapsed).lower()
    await page.evaluate(f"updateOverlayState('{self.overlay_processing_state}', {js_bool});")
except Exception as e:
    logger.debug(f"JavaScript error: {e}")
```
```python
# ui_manager.py :239-240 — second call targets a function defined NOWHERE
if not self.overlay_is_collapsed:
    await page.evaluate("focusOnOverlayInput();")
    await page.evaluate("commandExecutionCompleted();")   # grep total: 0 in JS
```
```javascript
// injectOverlay.js :783 — arbitrary message content executed as HTML
messageBubble.innerHTML = cleanMessage;
```

**Flow:** each defect is independent; none crashes today because their trigger paths are cold (show_overlay has no production caller; command_completed is never invoked). Failure modes once triggered: inverted mirror makes post-navigation restore re-open a UI the user closed (and vice-versa) until some click re-syncs via the `overlay_state_changed` bridge; a transient evaluate failure during `update_processing_state` leaves every future restored page rendering the OLD progress state while Python believes the push happened; the ghost evaluate throws inside command_completed's caller; innerHTML turns any page-derived text into script execution inside the agent's own chrome.
**Invariant:** treat this ledger as a porting checklist — for each item choose FIX (recommended: write False at :83; log-and-queue or re-push on next hook at :116-120; bind or delete :240; switch sink to textContent; store+clearInterval the :578 handle) or KEEP-with-comment (only defensible for innerHTML if rich text is a hard requirement). Never copy silently.

**Probe:** `cd /mnt/hdd/utopia/inspo/TheAgenticBrowser && grep -n 'overlay_is_collapsed = True' core/utils/ui_manager.py` → `83`; `grep -c 'logger.debug(f"JavaScript error' core/utils/ui_manager.py` → `1` (:120); `grep -rc 'commandExecutionCompleted' core/utils/ui_manager.py core/utils/ui/injectOverlay.js` → `1` and `0`; `grep -n 'messageBubble.innerHTML = cleanMessage' core/utils/ui/injectOverlay.js` → `783`. No upstream tests; deterministic source pins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "handle_navigation inject frame", limit: 4 });
// rank-1 UIManager.handle_navigation 42-69 anchors the ui_manager file where three of five sites live
```

## Verdict
Adopt the ledger as the port-time diff between "upstream behavior" and "correct behavior". Adapt fixes to your architecture. Omit nothing from the checklist — every item was verified by byte-exact grep at the pinned commit; none is speculative.
