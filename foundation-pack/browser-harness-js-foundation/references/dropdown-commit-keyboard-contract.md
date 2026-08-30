<!-- capsule-v2 -->
# dropdown-commit-keyboard-contract — how do native selects, custom overlays, and comboboxes each commit a value?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** Why must native selects be set via JS, and why do most comboboxes commit on the keyboard rather than a click?

## Per-kind commit contract
**Path/Symbol:** `skills/cdp/interaction-skills/dropdowns.md` whole doc — native `<select>` (:5–19), custom overlay (:21–50), searchable combobox (:52–68), virtualized menus (:70–72), Traps (:74–79).
**Signature:** native: `Runtime.evaluate` set `.value` + `dispatchEvent(new Event('change', { bubbles: true }))`. Combobox: click focus → `Input.insertText(search)` → wait render → `dispatchKeyEvent` ArrowDown (`windowsVirtualKeyCode: 40`) down+up → Enter (`windowsVirtualKeyCode: 13`, text:'\r') down+up.
**Data Shape:** three kinds: native select (JS-set; keyboard/mouse opens an OS menu CDP cannot close), custom overlay div-menu (click trigger → RE-MEASURE — options mount late/portal to body → coordinate-click option found by visible text), searchable combobox (Downshift/Radix/MUI commit on KEYBOARD).

### Decisive source
```md
Most comboboxes commit on the **keyboard**, not the click:
...
- MUI Autocomplete: `blur` commits the text value, not the selected option.
  Always use Enter.
```

**Flow:** classify rendered widget → native = evaluate-set + bubbling change event (verify by re-read) → overlay = open, re-measure, text-find option, coordinate-click → combobox = insertText + ArrowDown+Enter key events → Radix needs `Escape` to close WITHOUT committing (outside-click may keep stale input).
**Invariant:** Commit channel is per-widget-family and NOT interchangeable: clicking an OS-opened select menu does nothing; blurring MUI commits the wrong thing; portals mean options are NOT descendants of the trigger (search document-wide, never trigger.querySelectorAll). Virtualized lists only render the visible slice — wheel the menu container until the option mounts, THEN coordinate-click.
**Probe:** `grep -cF "new Event('change', { bubbles: true })" skills/cdp/interaction-skills/dropdowns.md` → 1; `grep -cF 'Re-measure' <same>` → 1; `grep -cF 'windowsVirtualKeyCode: 40' <same>` → 2; `grep -cF 'commits the text value' <same>` → 1; `grep -cF 'require `Escape` to close' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "dropdowns" (Module node resolves line-exact).

## Verdict
Adopt the kind-classification and the JS-set-vs-keyboard-commit split as portable doctrine. Adapt selector/text-matching details per design system. Omit the MUI-specific blur note only if you will never touch MUI Autocomplete.
