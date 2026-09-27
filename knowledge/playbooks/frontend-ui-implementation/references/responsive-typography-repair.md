# Repair Responsive Layouts and Typography Ownership

Use when intermediate widths still feel cramped despite passing overflow checks, text ignores shared tokens, or the user asks to organize scattered CSS. Repair the existing system; do not turn a local correction into a redesign or impose one giant stylesheet.

## 1. Reopen the acceptance contract

A passing suite does not settle visual acceptance. Check for changed requirements or missing coverage. Inspect current source and rendered screens, not the previous completion claim. Separate composition problems from font loading, role assignment, cascade and inheritance problems.

Record the required alignment, reading measure, columns, media crop, text roles and interactions for each affected template. Preserve accepted content, assets and unrelated behavior. Convert ambiguous requests into observable checks: “center the hero” can require both centered boxes and centered text, relative to the intended container.

## 2. Compose the intermediate layouts

Inspect narrow portrait, wider landscape and breakpoint boundaries, plus phone/desktop endpoints. Use content-fit thresholds, not device names; navigation, forms and narrative cards need not switch together.

Dense stories may need stacking while compact cards remain paired. Decide what wraps, stacks or scrolls without hiding useful copy or shrinking text merely to fit. Check proportional media, illustration clearance, article alignment and intrinsic heights. Centering a flex container does not override a child's explicit `text-align: left`.

## 3. Establish type ownership

Inventory all text: headings, body copy, quotes, figures, metadata, captions, navigation and form controls. Class-name searches alone miss semantic labels named “note” or “name.” Confirm actual fonts load before diagnosing their metrics.

Separate responsibilities using the project's architecture:

- Existing tokens own complete recipes and responsive scales.
- A shared typography layer or component API assigns semantic roles.
- Layout owners control geometry, surfaces and composition.

Consolidate competing or partial recipes; retain genuinely distinct roles and justified local variants. For broad migrations, parse CSS, preserve a recoverable snapshot and remove superseded declarations rather than append another override layer.

Low-specificity `:where(...)` mappings can let reusable type classes win predictably. Source order still matters between those mappings. Test precedence on real markup. The `font` shorthand does not reset `letter-spacing`; prevent prose nested in headings or links from inheriting display tracking.

## 4. Prove ownership, not just appearance

Use complementary checks:

- **Source guard:** enforce the agreed typography boundary, including responsive and inline styles. Account for font-face declarations, third-party styles and intentional exceptions; do not mistake a regex for a CSS parser.
- **Propagation probe:** collect rendered elements with direct text plus form controls, not only headings. Save styles, temporarily substitute distinctive complete role recipes, inspect computed family/weight/size/leading, and restore in `finally`. Scope out non-product chrome; extend traversal for relevant shadow roots or SVG text.
- **Assignment probe:** uniform substitution detects disconnected overrides, not whether the right role was chosen. Change one role or primitive separately; check its intended consumers, unrelated roles and reusable-class precedence. Audit tracking separately.
- **Composition probe:** assert requested alignment and column relationships, not just absence of horizontal overflow. Exercise navigation open/close, focus and resize/rotation state.

## 5. Review and explain reflow

Inspect viewport-sized and section screenshots alongside overview sheets; scaled full-page images can conceal crowding. Hide development chrome only in the capture harness, never product defects.

Investigate changed geometry before updating baselines. Temporarily restoring old tracking can show why unchanged font sizes now produce another line. Accept a reviewed reflow, not a guessed cause, weakened assertion or fixed-height workaround.

Report mechanical checks, visual judgment and user acceptance separately. Name untested browsers/devices; touch emulation is not physical-device verification. Keep exact project scales, counts and screenshots in project records, not this procedure.
