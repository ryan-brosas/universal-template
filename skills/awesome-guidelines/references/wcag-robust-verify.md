<!-- capsule-v2 -->
# Robust and verify — do components expose name/role/value and does AA verification cover the claim scope?

**Source:** WCAG 2.1 Principle 4; Understanding 4.1.1–3; WCAG conformance guidance. **Question:** Does assistive technology get correct semantics and is Level AA conformance evidenced?

## Robust seam
**Path/Symbol:** custom widgets, dynamic UI, design-system components.
**Signature:** programmatic name, role, state, value; status in live regions.
**Data Shape:** ARIA only when native element insufficient; valid HTML ids.

### Decisive pattern
```html
<button aria-pressed="false" aria-label="Add to favorites">★</button>
<div role="alert" aria-live="assertive">3 items added to cart.</div>
```

**Flow:** **4.1.1** valid markup — **unique IDs**, complete elements → **4.1.2** UI components expose **name, role, value, state** to accessibility API → prefer **native** `<button>`, `<input>`, `<select>` before ARIA widgets → custom components: correct `role`, `aria-*`, keyboard behavior per WAI-ARIA APG → **4.1.3** **status messages** use `role="status"`/`role="alert"`/`aria-live` so AT announces without focus move.
**Invariant:** div-button without role/name, duplicate ids, or silent dynamic updates fails Robust AA.
**Probe:** accessibility tree inspect (DevTools/axe); VoiceOver/NVDA spot check on changed widgets.

## Verify seam
**Flow:** declare **scope** (page, user journey, or site) and target **WCAG 2.1 Level AA** → run **automated** scan (axe, Lighthouse accessibility) on scoped URLs → **manual** keyboard-only pass + zoom 200% + sample screen reader → map failures to **SC numbers** → fix or document **exceptions** with user-impact rationale (rare) → re-run until scoped A+AA criteria pass → optional: publish conformance statement / VPAT pointer.
**Probe:**
```bash
# example — project-specific runner
npx playwright test tests/a11y/
axe-cli https://localhost:3000/checkout
```

**Invariant:** “axe clean” alone without keyboard/SR manual checks is insufficient for AA completion claim.
**Probe checklist:** full Tab path; focus visible; form errors; live regions; contrast sample.

## Verdict
Correct AT semantics plus scoped A+AA verification with automated + manual evidence. Learning note: `wcag-accessibility-learning-note.md`.
