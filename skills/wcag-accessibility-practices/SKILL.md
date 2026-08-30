---
name: wcag-accessibility-practices
description: "Use when auditing or building web UI for WCAG 2.1 Level AA, POUR success criteria, keyboard/focus, contrast/reflow, forms/errors, name-role-value, and axe plus manual verification."
disable-model-invocation: true
---

# WCAG Accessibility Practices

Application skill for W3C WCAG 2.1 Level AA ingest (`awesome-guidelines`). Semantic HTML baseline: `frontend-markup-practices`. Copy/docs a11y: `mailchimp-content-practices`, `google-devdocs-practices`.

## Core Principle

Accessible web content satisfies **WCAG 2.1 Level AA**, perceivable without vision-only cues, operable by keyboard, understandable forms/language, robust for assistive technology, verified with automated **and** manual checks.

## When to Use / NOT

- Shipping pages, flows, or components claiming AA conformance.
- PR review on UI, design tokens, forms, modals, SPAs.
- Accessibility audit before release or procurement.

**NOT when:**

- Static HTML/CSS style only, `frontend-markup-practices` (pair with this for SC coverage).
- Native iOS/Android apps, platform accessibility HIG primary.
- Marketing copy tone, `mailchimp-content-practices` (still pair for SC 2.4.4, 3.1.1).

## Workflow

1. **Perceivable**, alt text, structure, contrast, reflow (`wcag-perceivable-media-text.md`).
2. **Operable**, keyboard, focus, navigation, pointer/motion (`wcag-operable-keyboard-focus.md`).
3. **Understandable**, lang, predictability, forms/errors (`wcag-understandable-forms-language.md`).
4. **Robust**, name/role/value, status messages, verification (`wcag-robust-verify.md`).
5. **Verify**, scoped A+AA checklist + axe/Lighthouse + keyboard + screen reader sample.

## Red Flags

- Informative image missing `alt` or filename alt
- Color-only state/error (no text/icon)
- `<div>`/`<span>` click handlers without keyboard + role/name
- `outline: none` without visible `:focus-visible` replacement
- Placeholder used as only label
- Icon-only control without accessible name
- Modal without escape and focus restore
- Missing `<html lang="…">`
- Unexpected route/context change on focus/input
- “Click here” / “Read more” links out of context
- Duplicate `id` values in DOM
- Custom widget missing ARIA state updates
- Toast/alert visual-only, no live region
- AA claim from automated scan only
- Testing only mouse, never Tab/Shift+Tab

## Verification

- axe-core or Lighthouse on scoped URLs (zero serious/critical for claim scope)
- Manual keyboard-only traversal of changed flows
- 200% zoom + 320px width spot check
- Contrast check on text and UI components (4.5:1 / 3:1)
- Screen reader sample (NVDA/VoiceOver) on new widgets
- Failures mapped to WCAG 2.1 SC ids in review notes

## Skill Result Contract

```xml
<skill_result>
  <skill>wcag-accessibility-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>a11y report, SC mapping, fix diff</artifacts>
  <evidence>learning note + capsule probes + manual keyboard pass</evidence>
  <risks>keyboard trap, missing alt, or AA gap in untested flow</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/wcag-accessibility-learning-note.md`
- `awesome-guidelines/references/wcag-perceivable-media-text.md`
- `awesome-guidelines/references/wcag-operable-keyboard-focus.md`
- `awesome-guidelines/references/wcag-understandable-forms-language.md`
- `awesome-guidelines/references/wcag-robust-verify.md`

## Related skills

- `frontend-markup-practices`, semantic HTML/CSS separation
- `mailchimp-content-practices`, inclusive UI copy
- `google-devdocs-practices`, developer doc accessibility
