<!-- capsule-v2 -->
# rich-editor-probe-first — why does the accessibility tree lie inside canvas/virtualized editors, and what is the probe-before-bulk protocol?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** How do you type into Docs/Sheets/Figma-class surfaces without landing text in a hidden focus trap?

## Probe-then-bulk editing protocol
**Path/Symbol:** `skills/cdp/interaction-skills/rich-editors.md` whole doc — pattern (:9–25), "Why the DOM is wrong here" (:27–38), Traps (:40–52).
**Signature:** screenshot → coordinate-click surface → `Input.insertText(uniqueToken)` (one call, no per-keystroke timing) → verify token landed → only then bulk content.
**Data Shape:** editors keep the document in their OWN virtual model; surrounding DOM is app chrome — toolbars, menus, ACCESSIBILITY-COMPLIANCE FOCUS TRAPS, hidden IME textareas. axView faithfully shows a `textbox` for the focus-trap input; axType fills it; the text vanishes from view. Toolbar search boxes / title inputs / dialog fields OUTSIDE the document body DO work via the AX tree.

### Decisive source
```md
5. **If the probe is elsewhere** (title bar, toolbar search, hidden textarea)
   STOP using `axView` / DOM helpers for this surface — switch fully to
   screenshot-guided mouse + real keyboard.
```

**Flow:** identify editable surface visually → click it (moves caret into editor's own focus) → write probe token via insertText → verify via screenshot/export/state check → bulk content ONLY after verification; re-click the surface after any in-app modal (focus trap may have moved).
**Invariant:** A clean axView proves the TOOLBARS are targetable, not the document. The probe is cheap insurance against bulk content vanishing into a hidden textarea; skipping it converts a working session into silent data loss. Real input path (dispatchKeyEvent/insertText) beats Runtime.evaluate DOM writes because editor-specific event handlers can stash evaluate-driven state in unexpected places.
**Probe:** `grep -cF 'focus traps, hidden textareas, and offscreen iframes' skills/cdp/interaction-skills/rich-editors.md` → 1; `grep -cF 'unique token' <same>` → 1; `grep -cF 'STOP using' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "rich-editors" (Module node resolves line-exact).

## Verdict
Adopt probe-before-bulk as a universal rule for canvas/virtualized edit surfaces. Adapt verification channel per editor (screenshot vs export API). Omit nothing — this doc is already the minimal correct procedure.
