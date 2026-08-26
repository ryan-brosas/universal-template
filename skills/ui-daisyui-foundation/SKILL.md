---
name: ui-daisyui-foundation
description: Use when porting daisyUI's Tailwind-plugin machinery — plugin entry registries with include/exclude algebra, theme injection ladder over CSS-variable tokens, cascade-layer specificity ladders, hand-rolled CSS selector prefix scanning, responsive breakpoint-variant generation, and the wrapper-sandwich Tailwind compile-and-extract API.
---

# ui-daisyui: Tailwind CSS plugin & build kernel

## Use this for
Use when building a Tailwind v4 plugin from plain-CSS component sources, porting a design-token theme system (oklch variables + `color-mix` depth), implementing class prefixing across selectors/variables, generating static responsive variants without a JIT runtime, or compiling authored CSS through Tailwind's `compile()` API to extract just your own output. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/plugin-entry-registries.md` — how a plugin fans registry items into addBase/addComponents/addUtilities with include/exclude control.
- `references/theme-injection-ladder.md` — turning `themes: ["light --default", "dark --prefersdark"]` into exact base-layer selectors.
- `references/nest-css-layers-flatten.md` — hoisting authored `@layer daisyui.l1…` object blocks into Tailwind-callable styles.
- `references/cascade-layer-specificity-ladder.md` — controlling override precedence with layer nesting depth instead of `!important`.
- `references/selector-prefix-scanner.md` — character-level class/variable prefixing that survives strings, comments, escapes, and attribute selectors.
- `references/responsive-variant-pipeline.md` — static `md:`/`lg:` variant generation by recompiling per breakpoint.
- `references/wrapper-sandwich-compiler.md` — using Tailwind's `compile()` as a library and slicing your output between sentinel layers.

## Capsule map
- **Plugin entry registries** — `plugin-entry-registries`: `{name → item}` registries invoked with `{addBase|addComponents|addUtilities, prefix}`; include ∧ ¬exclude algebra; un-layerable variants registered at top level.
- **Theme injection ladder** — `theme-injection-ladder`: flag-parsed theme options → `:where(root)` default + `[data-theme]` + `:has(input.theme-controller:checked)` + prefers-dark media selectors, with single-theme dedup early return.
- **CSS-object layer flattening** — `nest-css-layers-flatten`: move selector keys out of `@layer …` blocks, re-wrap in accumulated at-rule chains, array-merge duplicate selectors.
- **Cascade-layer specificity ladder** — `cascade-layer-specificity-ladder`: `@layer daisyui.l1.l2.l3` nesting depth = precedence tier; `:where()` wrappers and private `--component-*` vars as override hooks.
- **Selector-prefix scanner** — `selector-prefix-scanner`: quote/comment/escape/attribute-aware scanner plus exclusion lists for vars (`--tw`, token prefixes) and foreign selectors; `prefix === 0` no-op sentinel.
- **Responsive variant pipeline** — `responsive-variant-pipeline`: top-level-only first-class breakpoint renaming, colon escaping, keyframes hoisted out of media queries, one media block per breakpoint.
- **Wrapper-sandwich compiler** — `wrapper-sandwich-compiler`: sentinel `@layer wrapperStart/End` around payload in `compile()`, brace-index extraction with typed errors; downstream CSS→JS objectify + fallback cleanup.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
daisyUI (MIT), `master@c6e1800bc15ab0287b8c2b802c126ccee6361beb`; Codebase Memory project `ui-daisyui` (full mode, generation 2026-08-25T20:02:29Z, 98,570 nodes / 101,691 edges). Coverage caveat: 67 parse-partial files — nearly all `src/components/*.css` (Tailwind at-riles defeat tree-sitter); cited CSS ranges were read directly. Live bun test evidence: 56 pass (addPrefix, nestCssLayers, pluginOptionsHandler suites); generateRawStyles suite runner-blocked (postcss absent, no node_modules).

## Full view (memory graph)
Revalidate `ui-daisyui` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the registry/plugin shape, theme-selector ladder, layer-nesting specificity control, prefix-scanner state machine, and sentinel-layer compile extraction as pure contracts. Adapt option names, theme vocabularies, breakpoint tables, and exclusion lists to your host library. Omit daisyUI's specific component catalog, CDN bundle packaging, docs site, and the hardcoded `0.25rem` spacing assumption unless your design system shares it.
