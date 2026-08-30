<!-- capsule-v2 -->
# CSS structure — can reviewers scan rules and find breakpoints?

**Source:** Code Guide §Declaration order, §Media queries; Google HTML/CSS §Formatting; CSS Guidelines §Syntax. **Question:** Is formatting consistent and are responsive rules discoverable?

## Formatting seam
**Path/Symbol:** stylesheet rulesets.
**Signature:** 2-space indent; lowercase; space after `:`; semicolon on every declaration.
**Data Shape:** one declaration per line for multi-prop rules; blank line between rules.

### Decisive pattern
```css
.declaration-order {
  /* positioning → box → typography → visual → misc */
  position: relative;
  display: flex;
  width: 100%;
  font: normal 14px/1.5 sans-serif;
  color: #333;
  background-color: #f5f5f5;
  border: 1px solid #e5e5e5;
}

@media (min-width: 480px) {
  .declaration-order { width: 50%; }
}
```

**Flow:** group related properties (or alphabetize — pick one project-wide) → co-locate `@media` with the rules they modify → organize files by component not page.
**Invariant:** responsive behavior must not live only in a distant `responsive.css` orphan block — future editors will miss it.
**Probe:** Stylelint/Prettier config matches documented order; media queries adjacent to base rules in component sections.

## Shorthand & specificity
**Flow:** prefer explicit longhands when setting subset of sides → use shorthand only when all values intentional → raise specificity via structure, not reactive `!important`.
**Invariant:** avoid `!important` as a fix for greedy selectors; proactive utilities (`.hidden`) only with documented pattern.
**Probe:** `!important` count near zero except utility trumps; shorthand not used to accidentally reset unrelated sides.

## Verdict
Adopt consistent formatting, grouped declarations, co-located media queries; omit reactive `!important`. Learning note: `frontend-style-learning-note.md`.
