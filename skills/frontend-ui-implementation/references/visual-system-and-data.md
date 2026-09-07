# Visual System and Data Implementation

## Motion timing

The PDF groups animation durations as **<100ms** (often imperceptible), **100–200ms** (micro-interactions), **200–300ms** (intermediate/micro-interactions), and **>300ms** (complex motion). Preserve these as starting heuristics, not browser or WCAG requirements. Duration follows distance, property, purpose, interruption, and perceived latency. Every nonessential transition needs a reduced-motion alternative; loading status must remain understandable when animation is removed.

## Visual semantics

- Give buttons, links, tags, inputs, selections, and statuses distinct roles in both semantics and appearance. Border radius alone is not enough when color, placement, and behavior imply the same affordance.
- Reserve the primary color and strongest contrast for actual priority. Build secondary, tertiary, destructive, and quiet treatments rather than painting every action primary.
- Use one coherent icon family when possible. Normalize optical box, stroke, fill, corner style, and baseline; a wrapper can equalize different source geometries without falsifying semantics.
- Define an elevation system instead of inventing shadows component by component. Modals require clear interaction isolation, focus management, and backdrop semantics; a shadow is polish, not modality.
- In dark themes, test perceived brightness and contrast. The PDF’s suggestion to reduce highly saturated colors is a useful starting hypothesis, not a fixed palette rule.
- Use subtle borders/striping only when they help row tracking. Sparse tables may need whitespace; dense tables may need restrained rules, sticky context, hover/focus states, and grouping.

## Images and maps

- Define aspect ratio, object fit, focal point, loading fallback, error fallback, and alt behavior. User-uploaded images may use a subtle inset boundary when edge contrast is unpredictable.
- Product illustrations should magnify the relevant feature while preserving enough context to remain truthful; do not fabricate capability or hide consequential complexity.
- Maps should include only the detail required for the task. Optimize payload and visual noise without removing labels, boundaries, or precision users need.
- Decorative images use `alt=""`; informative images need equivalent purpose. CSS backgrounds cannot carry required content.
- Country flags do not reliably identify language or locale. Pair flags with text, and prefer language/region names when that is the actual choice.

## Charts and quantitative displays

- Axes, units, baselines, domains, legends, and sample size must support truthful comparison. Do not choose a Y-axis maximum solely to make bars impressive; include a little headroom only when it preserves the correct baseline and interpretation.
- Avoid pie charts with many slices. The PDF suggests roughly **5–6** before grouping “Other”; instead choose the chart from the comparison task, keep meaningful categories distinguishable, disclose grouping, and offer exact accessible data.
- Ratings show vote/review count and, when consequential, distribution, recency, source, and uncertainty. An average without denominator is misleading.
- Use tabular numerals and alignment for comparable columns. Never encode meaning by color alone.

## Filters, results, and tables

- Show active-filter count and state with text/semantics, not only a red dot. Make clear how to inspect and clear filters.
- Preview result count when it is fast and stable; debounce/cancel stale requests and announce updates without flooding live regions. A count is not useful if it lies during asynchronous races.
- Responsive tables preserve the task. Choose among prioritized columns, named horizontal scrolling, a comparison-specific compact view, or labeled record cards. Do not silently discard critical columns or destroy row/column relationships.
- Test empty, one, many, huge, stale, partially loaded, permission-filtered, negative, decimal, and localized values.

## Verification

Inspect all roles and states in light/dark/high-contrast modes, color-vision simulation as a supplement, keyboard and screen reader, reduced motion, user images, missing assets, dense data, long labels, RTL, narrow width, and zoom. Verify chart claims against raw values and table/card transformations against the same task.
