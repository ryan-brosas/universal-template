# Practical Interface Heuristics

These checks distill Victor Ponamariov’s *100 Practical UI/UX Tips* into testable groups. They are starting hypotheses, not universal rules. Product context, user evidence, platform conventions, the design system, and current accessibility standards decide the implementation.

## Typography and content

- Make the page scannable with descriptive headings, lists where structure is truly list-like, and restrained emphasis.
- Use proximity and whitespace to bind headings, labels, and related content. Avoid ambiguous block separation and false bottoms.
- Keep body lines comfortably readable; tune line length and line height together rather than enforcing one magic number.
- Keep links recognizable without hover. Do not encode action, status, or hierarchy by color alone.
- Protect text over imagery with a stable contrast treatment; do not cover semantically important image regions.
- Use a coherent type scale and consistent hierarchy. Use tabular numerals where columns must align.
- Test real extremes: long names, localized strings, large values, truncation, wrapping, zoom, and reflow.

## Forms and validation

- Keep persistent labels. Show task-critical instructions and password rules before submission, near their controls.
- Minimize required input; prefill only when accurate, expected, editable, and privacy-safe. Preserve entered data after errors and across recoverable handoffs.
- Prefer a simple visual sequence. Use multiple columns only for tightly related compound values and verify reading/tab order.
- Match control to data: semantic input type, useful keyboard, autocomplete, password-manager compatibility, and content-sized fields.
- Use dropdowns only when they reduce effort. Expose a small meaningful set directly; support typing/search for large familiar sets.
- Prevent errors where possible. Put specific, actionable errors inline, focus or scroll to the first invalid field without disorienting the user, and announce errors accessibly.
- Positive validation should confirm genuinely difficult input, not add noise. Multi-step forms must reduce per-step complexity, show progress, preserve state, and allow backtracking.

## Navigation, actions, and attention

- Put common controls where the audience expects them; show current location and a clear next action.
- Keep primary navigation visible when space permits. “More” is a compromise, not a cure for weak information architecture.
- Enlarge hit areas, especially on touch, and separate frequent actions from destructive ones.
- Label unfamiliar icons and flags. Tooltips supplement—not replace—persistent task-critical information and keyboard/touch access.
- Establish one dominant action per decision context; style buttons, tags, links, and status chips as different roles.
- Prefer reversible undo for ordinary destructive actions. Use proportionate confirmation when reversal is impossible or consequences are severe.
- Reveal one timely hint at a time. Notifications stay brief, persistent enough to perceive, and link to durable detail when needed.

## Loading, empty, error, and success states

- Reserve geometry to prevent layout shift; keep button dimensions stable while loading.
- Place progress feedback in the region whose state changed. Avoid flashing indicators for imperceptibly short waits; communicate progress or alternatives during meaningful waits.
- Empty states explain why the space is empty and offer the relevant first or recovery action.
- Never strand the user: every error explains what happened in user language, preserves work, and offers a next step. Success must be perceivable.

## Visual semantics and data

- Use color, shape, size, borders, shadows, and motion consistently; do not let decorative treatments imply false affordance or grouping.
- Keep icon style and elevation coherent. Reserve the primary color for real priority.
- Label charts and show denominators/sample sizes where ratings or aggregates can mislead. Avoid overloaded pie charts and distorted scales.
- Make filtering consequences visible before commitment where feasible; show active-filter state and zero-result risk.
- Responsive tables should preserve task-critical comparisons: selectively retain columns, allow named horizontal scrolling, or transform rows into labeled records.

## Accessibility and context checks

- Test keyboard order, visible focus, semantic labels, target size, zoom/reflow, reduced motion, screen-reader announcements, and contrast against the project’s WCAG target.
- Decorative images use empty alternative text; informative images receive equivalent purpose, not a filename.
- Never rely on the PDF’s exact timing, count, color, or size recommendations as standards. Examples such as fixed animation bands, “5–7” dropdown options, delayed loaders, autofocus, or avoiding pure black are context-sensitive and must be tested. Autofocus can disorient users or summon a mobile keyboard; motion can violate preference or accessibility needs.
