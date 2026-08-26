---
name: recharts-foundation
description: 'Use when porting or reimplementing axis tick generation: nice-number step algorithms (adaptive/snap125), fixed vs extending domain strategies, value→pixel tick mapping with band offsets, collision-aware label filtering, categorical pixel inversion, and immutable d3-scale wrapping.'
---

# Recharts: chart scale & tick pipeline foundation

## Use this for
Use when building any numeric/category axis for a charting library: computing "nice" tick values, deciding whether ticks may extend the domain, mapping values to pixels across linear/point/band scales, thinning overlapping labels, and inverting pixel positions back to categories. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/nice-ticks-adaptive-step.md` — how a rough step is rounded up onto a magnitude grid (0.05/0.1 ratio quantization), the default `StepFunction`.
- `references/nice-ticks-snap125-step.md` — the opt-in {1,2,2.5,5}×10ⁿ ladder, exact-member epsilon guard, and correctionFactor-as-index semantics.
- `references/nice-ticks-calculate-step.md` — middle anchoring (0 is always a tick), zero-straddle ≥3 lift, and the correctionFactor recursion that converges tick count.
- `references/nice-ticks-domain-guards.md` — ±Infinity sentinel fills, single-value delegation, reversed-domain output reversal, and the 0.1·step rangeStep pad.
- `references/nice-ticks-single-value.md` — min===max centered tick fans across decimals/integers/zero branches.
- `references/nice-ticks-fixed-domain.md` — clamped variant: forced boundary append, post-round integer dedupe, short-circuit guards.
- `references/nice-ticks-decimal-arithmetic.md` — Decimal-walk rangeStep with infinite-loop fuse; signed digit counts powering both step algorithms.
- `references/nice-ticks-mode-dispatch.md` — combineNiceTicks three-arm funnel: none/auto-keyword/explicit modes → which generator runs.
- `references/nice-ticks-domain-widening.md` — how tick extremes grow the rendered domain, with the unexplained angle-axis exemption.
- `references/ticks-value-to-coordinate.md` — combineAxisTicks five-level precedence and band/angle offset quirks (#4271).
- `references/ticks-collision-filtering.md` — getTicks interval modes, direction sign from first coordinates, lazy DOM size measurement.
- `references/ticks-equidistant-search.md` — restart-vs-offset asymmetry between preserveStart and preserveEnd equidistant searches.
- `references/ticks-visibility-primitives.md` — isVisible/getTickBoundaries/getEveryNth signed-space algebra shared by every filter.
- `references/scale-resolution-wrapper.md` — string/'auto'/function scale resolution into the immutable RechartsScale wrapper (.map band positioning).
- `references/scale-categorical-inverse.md` — bisect-based nearest-category inversion supporting descending arrays, with data-point override.
- `references/axis-size-oscillation-latch.md` — ABA ring-history latch that freezes measured axis sizes to break render loops.

## Capsule map
- **Step rounding** — `nice-ticks-adaptive-step`: rough→nice step via magnitude-normalized ceil-grid; up-only rounding on Decimals.
- **Nice snapping** — `nice-ticks-snap125-step`: cyclic {1,2,2.5,5} ladder where correctionFactor advances index, not grid density.
- **Boundary search** — `nice-ticks-calculate-step`: 0-anchored boundaries + recursion convergence when the nice step overshoots the count.
- **Entry guards** — `nice-ticks-domain-guards`: Infinity sentinels, degenerate fan-outs, reversal, half-open-walk pad.
- **Degenerate fan** — `nice-ticks-single-value`: equal-endpoint ticks centered by digit-count grids.
- **Clamped generator** — `nice-ticks-fixed-domain`: boundary-append + integer dedupe without domain extension.
- **Precision substrate** — `nice-ticks-decimal-arithmetic`: Decimal accumulation and negative digit counts.
- **Mode funnel** — `nice-ticks-mode-dispatch`: none/auto/adaptive/snap125 dispatch over evaluated-vs-declared domains.
- **Domain growth** — `nice-ticks-domain-widening`: min/max merge of tick extremes into the axis domain (angle axes exempt).
- **Pixel mapping** — `ticks-value-to-coordinate`: precedence user-ticks > niceTicks > categorical > scale.ticks > domain walk, plus band/angle offsets.
- **Label thinning** — `ticks-collision-filtering`: preserveStart/End sweeps shrinking usable span by measured half-width + gap.
- **Even spacing** — `ticks-equidistant-search`: whole-restart start anchor vs offset arithmetic end anchor per stepsize.
- **Visibility algebra** — `ticks-visibility-primitives`: signed bounds tests ordered before DOM reads; n-th picking semantics.
- **Scale objects** — `scale-resolution-wrapper`: name validation ('auto'→point/band/linear by chart kind), copy-before-mutate, .map() band positions.
- **Inverse mapping** — `scale-categorical-inverse`: cached pixel positions + direction-aware bisect + left tie-break.
- **Feedback-loop brake** — `axis-size-oscillation-latch`: five-condition ABA swallow on measured width/height updates.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Pass-1 plane = util/scale + tick selectors/filters; see work record NEXT-PASS TARGETS before deepening (polar tick paths, tooltip tick twin, CartesianGrid/Label planes are unmined).

## Provenance
recharts (MIT), `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory project `ext-ui-recharts` (FULL mode, 9,132n/39,454e, generated 2026-08-23T11:12Z, head=base at capture, parse_partial ×1 confined to www demo view; coverage stdin-check ×14 cited paths all no_recorded_issue+metadata_match).

## Full view (memory graph)
Revalidate `ext-ui-recharts` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/ui-recharts`, branch main, head_sha=base_sha `d56d6660…`, 9,132 nodes / 39,454 edges, status ready, generation_matches=true. BM25 retrieval is symbol-strong on this repo (all cited functions resolve line-exact); action creators like `updateYAxisWidth` are exported consts and NOT graph Function nodes — retrieve the slice file node instead. trace_path on `combineNiceTicks` enumerates the full callee lattice (getDomainDefinition, isWellFormedNumberDomain, calculateStep, getNiceTickValues, getTickOfSingleValue, getTickValuesFixedDomain, getValidInterval, rangeStep, getDigitCount). Gate-5 battery executed real repo source under node v26.7.0 --experimental-strip-types with resolve/load hooks (decimal.js-light vendored from a sibling checkout; type-only named imports stripped; react/reselect/redux-toolkit/immer/es-toolkit/victory-vendor stubbed) — 42/42 GREEN twice incl. upstream spec pins; vitest runner itself BLOCKED (no node_modules repo-wide) so direct-test claims cite upstream specs byte-pinned per capsule.

## Boundaries
Adopt the pure contracts: step algorithms, guards, visibility algebra, inversion, immutability discipline (framework-free math). Adapt host-specific integration: redux slice plumbing, createSelector memoization wrappers, getStringSize DOM measurement, react context providers. Omit product surface: www demo app, storybook stories, test-vr snapshots, chart-type components (Line/Bar/Pie render trees), polar tick paths not yet mined this pass.
