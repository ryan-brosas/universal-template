<!-- capsule-v2 -->
# Understandable — are language, behavior, and forms predictable with clear errors?

**Source:** WCAG 2.1 Principle 3; Understanding 3.1.1, 3.2.1–2, 3.3.1–4. **Question:** Do users know the page language, what will happen on interaction, and how to fix form errors?

## Language seam
**Path/Symbol:** HTML document and localized fragments.
**Signature:** `lang` on root and parts; plain labels.
**Data Shape:** `<html lang="en">`, `<span lang="fr">…</span>`.

### Decisive pattern
```html
<html lang="en">
  <label for="email">Email address</label>
  <input id="email" name="email" type="email" autocomplete="email" required
         aria-describedby="email-hint">
  <p id="email-hint">We never share your email.</p>
```

**Flow:** **3.1.1** set **`lang`** on `<html>` → **3.1.2** mark foreign **language of parts** → **3.2.1** no **context change on focus alone** (no auto-submit on tab) → **3.2.2** no **unexpected context change on input** without warning → keep navigation **consistent** (**3.2.3** AA on repeated components).
**Invariant:** missing page `lang` or focus-triggered navigation without consent fails Understandable review.
**Probe:** validator `lang`; focus each control — no surprise route change.

## Forms and errors seam
**Flow:** **3.3.2** every input has **visible label** or instructions (not placeholder-only) → associate via `for`/`id` or `aria-labelledby` → **3.3.1** errors identified in **text** (not color alone) → link error to field (`aria-invalid`, `aria-describedby`) → **3.3.3** offer **correction suggestions** when deterministic → **3.3.4** legal/financial/data submissions **reversible, checked, or confirmed**.
**Invariant:** placeholder-as-label, color-only invalid state, or silent submit failure fails form AA.
**Probe:** submit empty required form — errors readable by screen reader; axe label checks.

## Verdict
Declared language, predictable interactions, labeled inputs, textual errors with suggestions. Learning note: `wcag-accessibility-learning-note.md`.
