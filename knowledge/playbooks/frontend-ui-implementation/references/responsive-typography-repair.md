# Repair Responsive Layouts and Cross-Page Typography

Use when intermediate widths feel cramped, text ignores tokens, or pages look inconsistent despite centralized CSS and passing checks. Repair the existing system rather than redesigning it. Token connection does not prove correct semantic assignment.

## 1. Reopen the acceptance contract

Inspect current source and rendered screens, not the previous completion claim. Separate composition, font loading, role assignment, cascade and inheritance problems.

Record alignment, reading measure, columns, media crop, text roles and interactions. Resolve any conflict between source fidelity and requested cross-page uniformity; do not silently preserve outdated per-page exceptions or flatten intentional emphasis. Keep accepted content, assets and behavior. Supersede stale acceptance notes when requirements change.

## 2. Compose the intermediate layouts

Inspect portrait, landscape and breakpoint boundaries, plus phone/desktop endpoints. Use content-fit thresholds, not device names; navigation, forms and narrative cards need not switch together.

Decide what wraps, stacks or scrolls without hiding copy or shrinking text. Check media proportions, artwork clearance and intrinsic heights. Centered boxes do not guarantee centered text or alignment to the intended container.

## 3. Define an independent role map

Inventory rendered text across affected page families, including direct text nodes and controls. Confirm real fonts and weights load before comparing metrics.

Group text by purpose and hierarchy, not its current CSS, tag or class name: page titles, introductions, reading prose, card/list/step summaries, section/card headings, primary/secondary labels, figures and captions. Sweep related-reading descriptions, compact invitations, nested links and notices too; inspecting heroes alone misses secondary inconsistencies.

Record route/template + consumer + expected role + justified exception. Derive expectations from content intent, not the production selector-to-token mapping; copying a wrong mapping into a test proves nothing. Equivalent content should share a role, while genuine hero, quote, story or example emphasis can remain distinct. Uniformity does not mean every heading or paragraph looks alike.

## 4. Establish type ownership

Use the project's architecture:

- Existing tokens own complete recipes and responsive scales.
- A shared typography layer or component API assigns roles.
- Layout owners control geometry, surfaces and composition.

Reuse or alias equivalent roles rather than duplicate recipes. Consolidate partial recipes and remove superseded overrides; for broad migrations, parse CSS and retain a recoverable snapshot.

Low-specificity `:where(...)` mappings can let reusable classes win, but source order still matters. Test real markup and class precedence. The `font` shorthand does not reset `letter-spacing`; nested prose can inherit display tracking.

## 5. Prove connection, assignment and isolation

Use complementary checks:

- **Source guard:** enforce the typography boundary, including responsive/inline styles. Account for font-face declarations, third-party styles and justified exceptions. Do not mistake a regex for a CSS parser.
- **Whole-text propagation:** save styles, substitute distinctive complete recipes, inspect direct-text elements and controls, then restore in `finally`. Exclude non-product chrome; cover relevant shadow roots or SVG text. Changing all roles and accepting any replacement proves connection, not correct assignment.
- **Semantic assignment:** compare each mapped consumer against its intended role at relevant widths: family, weight, size, leading and tracking. Assert required consumers exist. Lock agreed responsive scales separately where the product contract specifies them.
- **Isolated mutation:** change one role at a time; its consumers must follow and an unrelated role must remain unchanged. This catches wrong bindings even when two recipes currently look identical. Account for intentional aliases; test tracking and reusable-class precedence separately.
- **Composition:** assert alignment, column relationships and navigation open/close, focus and resize/rotation state, not merely zero overflow. Where feasible, establish that the new assertion rejects the pre-repair mismatch before accepting the fix.

## 6. Review and explain reflow

Compare page-family overview sheets at the same viewport, then inspect full-size sections, including secondary copy. Scaled full-page images conceal crowding. Hide development chrome only in the capture harness.

Correct roles can change line counts and section heights. Adjust reading columns, intrinsic shared grid rows or stacking rather than shrinking type, clipping copy or fixing heights to conceal overflow. Investigate geometry before updating baselines; temporarily restoring old tracking can isolate a wrapping cause. Accept a reviewed reflow, not a weakened assertion.

Refresh affected captures after final edits. Report mechanical checks, visual judgment and user acceptance separately. Name untested browsers/devices; emulation is not physical-device verification. Keep project scales, counts and screenshots in project records, not this procedure.
