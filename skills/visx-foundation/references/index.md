<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# visx: Chart Primitive Kernel Foundation

## Use this for
Use when porting or reimplementing visualization primitives: d3-scale config application with correct operator ordering, keyboard-navigable + screen-reader-accessible charts, pixel-to-domain brush selection with ordinal support, cursor-anchored zoom transforms, parent-size responsiveness without layout loops, SVG text measurement/wrapping, animated line enter/exit trajectories, and referentially-stable data/accessor plumbing. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./scale-operator-pipeline.md` — In what order do scale config keys apply (`domain→nice→zero`, `interpolate→round`, `range→reverse`) and why does reordering silently change results?
- `./scale-zero-descending-domain.md` — How do you extend a scale domain to include 0 without un-reversing descending domains?
- `./scale-nice-utc-detection.md` — How do you `nice()` a time scale by interval without corrupting UTC charts (format-probe UTC detection)?
- `./scale-copy-on-update-contract.md` — Why must updateScale call `scale.copy()` and when do memoized hook scales rebuild?
- `./scale-round-interpolate-conflict.md` — What happens when a config sets both `round` and `interpolate`, and how does round work on scales without `.round()`?
- `./a11y-keyboard-state-machine.md` — What pure reducer gives charts roving point navigation with wrap-around, series jumps, and Enter/Exit memory over ragged series?
- `./a11y-roving-focus-plumbing.md` — How does keyboard state become real DOM focus (element map, delete-on-null registration, threshold gating)?
- `./a11y-aria-tree-density-gate.md` — Which ARIA roles/labels go on svg/series/point, and why are point labels dropped above 150 points instead of truncated?
- `./a11y-description-dispatch.md` — How is chart data summarized into one sentence for dense vs small vs pie charts?
- `./a11y-hidden-data-table.md` — How do you expose full chart data to screen readers via a visually-hidden escaped table twin?
- `./a11y-composition-hook.md` — How do aria props, keyboard nav, announcer, and table compose into one hook result without prop clobbering?
- `./a11y-data-normalization-ladder.md` — How are flat/nested/per-series inputs normalized, and why does nested detection require >1 configured series?
- `./brush-extent-state-machine.md` — How does one component own select/move/resize brushing (the `-1` sentinel, delta clamping, resize-ratio rescale)?
- `./brush-pixel-domain-conversion.md` — How is a dragged rectangle converted to domain values for continuous AND ordinal scales (±SAFE_PIXEL nudge)?
- `./drag-state-hook.md` — How do dx/dy semantics, controlled `isDragging`, snap-to-pointer, and path restriction compose in a drag primitive?
- `./zoom-transform-matrix.md` — Why does zoom-around-a-point compose T∘S∘T⁻¹, and how does a matrix ref beat stale wheel-event state (reject-not-clamp constraint)?
- `./responsive-parent-size-debounce.md` — Why does ParentSize need a leading-edge debounce, and what is the changed-keys-only ignoreDimensions bail rule?
- `./text-measure-wrap-fit.md` — How is SVG text measured/wrapped without DOM layout, and why does `scaleToFit:true` differ from `'shrink-only'`?
- `./spring-enter-exit-trajectory.md` — Where do animated lines come from/go to, especially on SVG's inverted y-axis (min/max flip)?
- `./kernel-structural-memo-accessors.md` — How do structural memoization and source-text accessor inference keep inline props referentially stable?
- `./kernel-domain-nan-quarantine.md` — How is a scale domain derived from raw data without NaN poisoning, and what do empty datasets yield?
- `./kernel-path-builder.md` — How do you emit precision-controlled SVG path strings (relative-command rects, two-segment full-circle arcs)?

## Capsule map
- **Scale plane** — `scale-operator-pipeline`: canonical-order operator pipeline (`ALL_OPERATORS` filter preserves execution order); feature-detection guards make one operator table serve all 14 scale types.
- **Scale plane** — `scale-zero-descending-domain`: zero-extension normalizes direction (`b<a`), widens with min/max against 0, restores orientation; same convention reused by spring configs.
- **Scale plane** — `scale-nice-utc-detection`: UTC vs local detected by formatting a fixed instant (`2020-02-02 03:04`), then interval tables chosen accordingly; `.every(step)` null = silent skip.
- **Scale plane** — `scale-copy-on-update-contract`: `applyAllOperators(scale.copy(), config)` never mutates caller scales; `useScale` memos on config identity (inline literals rebuild every render).
- **Scale plane** — `scale-round-interpolate-conflict`: explicit interpolate wins with console.warn; continuous scales emulate round via `interpolateRound` swap (double-cast required).
- **A11y plane** — `a11y-keyboard-state-machine`: two-mode reducer over `seriesLengths`; modulo wrap, empty-series-skipping column-preserving series jumps, exit preserves `lastFocusedPoint`, unchanged states return same ref.
- **A11y plane** — `a11y-roving-focus-plumbing`: Map-keyed element registry with delete-on-null, effect-driven `.focus()`, single `tabIndex 0`, exit refocuses SVG root, nav gated at ≤150 points.
- **A11y plane** — `a11y-aria-tree-density-gate`: `graphics-document/object/symbol` ladder; density gate drops point props but PRESERVES array-of-arrays shape; pie labels carry computed share.
- **A11y plane** — `a11y-description-dispatch`: override → empty → pie → dense (>threshold/scatter/heatmap) → small-series narrative; non-finite y filtered before stats.
- **A11y plane** — `a11y-hidden-data-table`: clip-rect hidden style keeps table in a11y tree; every cell HTML-escaped; ragged columns padded with `''`; announcer maps politeness to status/alert roles.
- **A11y plane** — `a11y-composition-hook`: spread order is load-bearing (keyboard overrides aria); components returned from hooks; `useId` sanitized into stable ids.
- **A11y plane** — `a11y-data-normalization-ladder`: series-config > nested-array (requires >1 series) > flat-wrap; label ladder fn > string > 'Data'/`Series N`.
- **Brush plane** — `brush-extent-state-machine`: `brushingType` discriminates select/move/edge/corner; `-1` extent = no selection; move clamps DELTA not position; container resizes scale selections by ratio.
- **Brush plane** — `brush-pixel-domain-conversion`: ordinal fallback indexes by step-walk when no `.invert()`; ±SAFE_PIXEL=2 outward nudge keeps edge clicks non-empty; result shape `{start,end}` XOR `{values}`.
- **Interaction plane** — `drag-state-hook`: dx/dy relative to start with grab-offset preservation; controlled `isDragging` syncs via effect; path samples beat box clamps exclusively.
- **Interaction plane** — `zoom-transform-matrix`: focal-point zoom composes translate∘scale∘translate⁻¹ around inverse-mapped point; constraint rejects (returns prev) instead of clamping; `matrixStateRef` mirrors state for stale wheel listeners.
- **Responsive plane** — `responsive-parent-size-debounce`: RO → rAF → leading-call debounce (first paint instant, trailing coalesces); bail only when EVERY changed key is ignored.
- **Text plane** — `text-measure-wrap-fit`: canvas-measured greedy wrap gated on width/scaleToFit; NBSP preserved; vertical anchor via reduce-css-calc; shrink-only caps scale at 1×.
- **Spring plane** — `spring-enter-exit-trajectory`: trajectory table center/min/max/outside with mandatory min↔max flip for SVG's inverted y; outside picks nearest range edge per line.
- **Kernel plane** — `kernel-structural-memo-accessors`: render-phase ref write keeps identity stable (depth 0 Object.is / depth 1 Date-aware shallowEqual); accessor source-text inference caches `d=>d.key` arrows by key.
- **Kernel plane** — `kernel-domain-nan-quarantine`: invalid values dropped (nulls silent, non-null-invalid counted+warned); empty yields `[0,0]`/epoch pair — never throws.
- **Kernel plane** — `kernel-path-builder`: fluent builder with toFixed precision; rects use relative h/v to avoid rounding drift; ≥TAU arcs split in half.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
visx (ui-visx fork with a11y/registry/kernel extensions) (MIT), `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory project `ext-ui-visx` (root `$REFERENCE_ROOT/external/ui-visx`, branch master, FULL mode 7,168n/22,410e, generation 2026-08-23T11:13:30Z, generation_matches=true, head_sha==base_sha zero drift; parse_partial ×26 = barrel index.ts re-export files + demo pages/css, none cited in capsules).

## Full view (memory graph)
Revalidate `ext-ui-visx` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Pass-1 evidence: all 29 cited paths `no_recorded_issue`+`metadata_match` via stdin-JSON coverage check; every capsule Retrieve resolves line-exact via `search_graph` ids mode; adversarial wrong-project queries (`transitionChartA11yKeyboardState`@ext-ui-tanstack-query, `applyZero scaleOperator`@ext-react) return total:0. Note: local variables (`startDy`) are not graph tokens — query the enclosing function instead. The `packages/visx-registry` package is shadcn-CLI distribution items with no runtime API (not mined); `visx-vendor` re-exports upstream d3.

## Boundaries
Adopt pure contracts (operator pipeline, state machines, matrix algebra, debouncer, path builder, converters); adapt React-specific wiring (hook composition, render props, class component lifecycle) to your host framework; omit product surfaces (visx-demo gallery, visx-registry shadcn items, storybook configs) and the @visx/vendor re-export layer (depend on d3 directly or keep vendor indirection consciously).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`a11y-aria-tree-density-gate.md`](./a11y-aria-tree-density-gate.md)
- [`a11y-composition-hook.md`](./a11y-composition-hook.md)
- [`a11y-data-normalization-ladder.md`](./a11y-data-normalization-ladder.md)
- [`a11y-description-dispatch.md`](./a11y-description-dispatch.md)
- [`a11y-hidden-data-table.md`](./a11y-hidden-data-table.md)
- [`a11y-keyboard-state-machine.md`](./a11y-keyboard-state-machine.md)
- [`a11y-roving-focus-plumbing.md`](./a11y-roving-focus-plumbing.md)
- [`brush-extent-state-machine.md`](./brush-extent-state-machine.md)
- [`brush-pixel-domain-conversion.md`](./brush-pixel-domain-conversion.md)
- [`drag-state-hook.md`](./drag-state-hook.md)
- [`kernel-domain-nan-quarantine.md`](./kernel-domain-nan-quarantine.md)
- [`kernel-path-builder.md`](./kernel-path-builder.md)
- [`kernel-structural-memo-accessors.md`](./kernel-structural-memo-accessors.md)
- [`responsive-parent-size-debounce.md`](./responsive-parent-size-debounce.md)
- [`scale-copy-on-update-contract.md`](./scale-copy-on-update-contract.md)
- [`scale-nice-utc-detection.md`](./scale-nice-utc-detection.md)
- [`scale-operator-pipeline.md`](./scale-operator-pipeline.md)
- [`scale-round-interpolate-conflict.md`](./scale-round-interpolate-conflict.md)
- [`scale-zero-descending-domain.md`](./scale-zero-descending-domain.md)
- [`spring-enter-exit-trajectory.md`](./spring-enter-exit-trajectory.md)
- [`text-measure-wrap-fit.md`](./text-measure-wrap-fit.md)
- [`zoom-transform-matrix.md`](./zoom-transform-matrix.md)
