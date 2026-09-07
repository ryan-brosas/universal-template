# Layout, Navigation, and Attention Implementation

## Layout and grouping

- Use proximity, common region, similarity, alignment, and whitespace so visual groups match semantic groups. A heading must travel with its content across breakpoints.
- Avoid false bottoms: large whitespace, footer-like bands, full-height heroes, rules, carousels, or card edges must not imply the page or menu has ended. Let part of the next meaningful section show when continuation is otherwise ambiguous.
- Do not shrink text to fit navigation or dense layouts. Rework labels, grouping, information architecture, wrapping, or overflow behavior first.
- Align mixed text/icon rows optically; `align-items: baseline` often works for text-bearing items, while icon geometry may need a consistent wrapper.
- Overlap is decorative, not structural. It must not obscure content, break focus order, clip at zoom, or create false grouping.

## Navigation

- Put common controls where the product’s audience and platform conventions predict them. Innovation must beat the learned convention in task evidence.
- Keep primary desktop navigation visible when space permits. A hamburger or “More” menu is a constrained fallback, not a way to avoid information architecture.
- Put frequent options first only when trustworthy task evidence supports the ordering; preserve less-common paths and let users control or reset personalization.
- Avoid carousels by default. If one is justified, make every item discoverable, preserve DOM/reading order, provide labeled previous/next and position, pause autoplay, support touch and keyboard, and announce changes without flooding assistive technology.
- Choose horizontal versus vertical navigation from depth, item count, label length, available space, and task frequency—not aesthetics alone. Keep sidebars content-sized or token-bounded rather than stretching with an unrelated fluid grid.
- Show current location with an active state that is not color-only. Use breadcrumbs for meaningful hierarchy; every crumb is a real destination unless it names the current page.
- Preserve keyboard shortcuts, focus order, open-menu state, selected location, and return focus across responsive transformations.
- Enlarge the actual interactive box with padding rather than a disconnected invisible overlay. Meet the project target-size criterion and leave enough separation from adjacent/destructive actions.

## Action hierarchy and safety

- One action should dominate a single decision context; secondary, tertiary, link, destructive, tag, and status treatments must remain distinguishable.
- Separate frequent actions from destructive ones spatially and visually. Prefer undo for ordinary reversible deletion; require proportionate confirmation for high-cost or irreversible operations.
- Label unfamiliar icons visibly. An accessible name is necessary but does not make an ambiguous icon understandable to sighted users; hover-only tooltips are insufficient on touch and keyboard.
- Put slider values where the hand or pointer does not cover them, typically above on touch layouts. Announce the current value semantically.

## Attention without manipulation

- Establish hierarchy by reducing competing salience before adding stronger color, weight, animation, or overlays.
- Show one timely hint when possible; queue or consolidate competing guidance. Never hide critical warnings merely to reduce visual load.
- Keep transient notifications concise and link to durable detail. Users must have enough time, pause/dismiss behavior where needed, and access to the message after it disappears.
- Search-focus overlays, faces, gaze, fingers, animation, and dimming are hypotheses. Use them only when they improve task focus without obscuring navigation, trapping focus, inducing motion, or manipulating a material choice.
- Time welcome messages and cross-channel notifications around user value and urgency; do not interrupt an active mobile task for nonessential promotion.

## Responsive behavior

Specify what wraps, stacks, scrolls, condenses, or moves at content-driven breakpoints. Preserve reading/focus order, current location, primary action, context, and task-critical information at narrow width, landscape, zoom, virtual-keyboard display, RTL, and long localization.

## Verification

Render navigation open/closed/current, every breakpoint, longest labels, 200% zoom, RTL, keyboard focus, touch targets, sticky headers/banners, destructive adjacency, and page/menu continuation. Confirm no control becomes hidden solely to fit and no visual transform changes semantic or tab order unexpectedly.
