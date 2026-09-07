# How are optional window settings normalized at the native boundary?

Source: [remorses/gpuix](https://github.com/remorses/gpuix) at `a24b4a42eb516c7b940eb8d34ecebb077df623bd`, Apache-2.0. Historical source evidence; current project requirements and runtime tests outrank this capsule.

## Entry and data flow

`packages/native/src/renderer.rs:5466-5493` defines the N-API `WindowOptions` object. `Default` at :5495-5515 supplies explicit values, but incoming fields can still be absent. `to_gpui_window_options` at :5517-5559 independently normalizes those absent fields before constructing GPUI options. This distinction is why testing only Rust `Default` would miss the foreign-language omission path.

The mapper uses `unwrap_or(true)` independently for focus and show. Explicit false survives; one does not imply the other. Background precedence is a recognized `window_background` string, then the legacy transparent flag, then opaque. Unknown strings do not raise a validation error. Minimum size and traffic-light position each require both coordinates; a partial pair becomes None. Fullscreen changes the bounds variant. Remaining native fields use GPUI defaults.

## Invariants and failure boundaries

- Missing focus/show is different from explicit false; mapping defaults must match object defaults.
- String handling is fallback-based, not strict validation. Don't describe an unknown background string as rejected.
- Partial paired dimensions are discarded, not independently applied. Numeric finiteness/range validation is not established by this function.
- Mapping is pure construction: it does not own callbacks or disposal. Focus/show are documented as ignored on Linux; a mapping test does not prove compositor behavior.
- Neither this pinned upstream struct nor `packages/native/index.d.ts:502-537` exposes appId. Heddlework's patch adds it; do not attribute that downstream feature to upstream.

## Direct tests

Read `renderer.rs:5898-5972`: `defaults_open_a_focused_visible_window`, `unset_focus_and_show_still_default_to_true`, `focus_false_leaves_the_window_visible`, `show_false_keeps_focus_independent`, and `existing_options_are_still_mapped`. The first two distinguish object defaults from missing-option normalization. The next two establish independent flags. The final test checks title, resize, blurred background, and paired minimum dimensions. These do not prove invalid-string fallback, partial pairs, numeric validation, or Linux window behavior. Upstream tests were read, not executed; no dependency installation or setup.

## Active-project comparison

Heddlework's `tests/window-options.test.ts` checks Linux app identity against desktop Icon/StartupWMClass and absence on macOS/Windows, macOS custom chrome, browser initialization configuration, and native titlebars on Linux/Windows. `src/window-options.ts` owns application policy; the tracked GPUIX patch owns native forwarding. Local option-object assertions are not evidence of a running compositor accepting identity.

**Disposition: ADAPT.** Reuse the explicit omission-versus-false normalization seam for downstream bridge extensions, but preserve Heddlework's platform policy and independently test the native forwarding. Do not copy upstream platform assumptions as application defaults.

## Scope and retrieval

One pure bridge-normalization seam only. Read the mapper and adjacent named tests at the pinned revision before reuse. Existing graph `heddlework-inspo-gpuix-0.7.0` includes the Zed submodule; scope retrieval to `packages/native/` rather than treating nested GPUI evidence as GPUIX-owned behavior. This pass used direct reads; graph completeness is not asserted. No whole-repository or live-runtime validation claim.
