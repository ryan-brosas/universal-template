<!-- capsule-v2 -->
# Operable — is all functionality keyboard reachable with visible focus and safe motion?

**Source:** WCAG 2.1 Principle 2; Understanding 2.1.1, 2.1.2, 2.4.3, 2.4.7, 2.5.1–4. **Question:** Can users operate, navigate, and orient without pointer-only or seizure/motion barriers?

## Keyboard seam
**Path/Symbol:** interactive pages, SPAs, modals, widgets.
**Signature:** full keyboard path; no trap; visible focus.
**Data Shape:** native `<button>`, `<a href>`, focusable custom elements with ARIA.

### Decisive pattern
```html
<a href="#main" class="skip-link">Skip to main content</a>
<main id="main" tabindex="-1">…</main>
<button type="button" aria-expanded="false" aria-controls="menu">Menu</button>
```

**Flow:** **2.1.1** all functionality operable via **keyboard** (except path-dependent drawing) → **2.1.2** user can **exit** every focused region — modals restore focus → **2.1.4** single-character shortcuts **off/remap** when focused → **2.4.1** **bypass blocks** (skip link/landmark) → **2.4.2** unique descriptive **`<title>`** → **2.4.3** **logical tab order** matches visual reading order → **2.4.7** **visible focus indicator** (also check **1.4.11** contrast) → **2.2.1/2.2.2** user can extend/pause moving/auto-updating content → **2.3.1** no flashing > **3 Hz**.
**Invariant:** pointer-only control, missing focus ring, or keyboard trap fails Operable AA.
**Probe:** Tab through full flow; Shift+Tab out of modals; check `:focus-visible` styles; pause carousels.

## Pointer and motion seam
**Flow:** **2.5.1** multipoint/path gestures have **single-pointer** alternative → **2.5.2** activate on **up-event**; abort before completion → **2.5.3** **visible label** substring in accessible name → **2.5.4** motion actuation has UI alternative and disable setting → **2.4.4/2.4.6** link text and headings **descriptive**.
**Invariant:** drag-only action without tap alternative, or shake-to-undo without off switch, fails 2.5.x.
**Probe:** operate with keyboard only; test drag handles for click alternative; review link text out of context.

## Verdict
Keyboard-complete flows, visible focus, navigable structure, pointer/motion alternatives. Learning note: `wcag-accessibility-learning-note.md`.
