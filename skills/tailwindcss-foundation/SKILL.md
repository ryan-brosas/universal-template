---
name: tailwindcss-foundation
description: "Use when porting Tailwind CSS v4 compiler mechanics — the `compile()`/`compileAst()` incremental build kernel, `@theme` design-system ingestion and resolution, candidate parsing/compilation and its deterministic sort ladder, or the variant application protocol — into another utility-CSS engine or a host integration (Vite/PostCSS/CLI driver). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# tailwindcss: v4 core compiler foundation

## Use this for
Use when porting Tailwind CSS v4 compiler mechanics — the `compile()`/`compileAst()` incremental build kernel, `@theme` design-system ingestion and resolution, candidate parsing/compilation and its deterministic sort ladder, or the variant application protocol — into another utility-CSS engine or a host integration (Vite/PostCSS/CLI driver). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/incremental-build-kernel.md` — How does `build()` stay cheap across rebuilds, and which three short-circuit tiers must a reimplementation preserve?
- `references/candidate-sort-ladder.md` — How are compiled utilities ordered deterministically regardless of source scan order?
- `references/design-system-memo-lattice.md` — How does one DesignSystem object memoize parse and compile work without leaking invalid results?
- `references/variant-application-protocol.md` — When does a variant make a rule inapplicable, and how do compound variants compose without cross-contamination?
- `references/theme-namespace-reset.md` — How do `--ns-*: initial`, `default`, and user overrides interact when folding many `@theme` blocks into one Theme?
- `references/theme-resolve-var-inline.md` — When does theme resolution emit `var(--key)` versus an inline value, and what does REFERENCE mode imply?
- `references/at-theme-ingestion.md` — How is `@theme` CSS folded into one output `:root, :host` rule while keyframes survive hoisting?

## Capsule map
- **Incremental build kernel** — `incremental-build-kernel`: accumulate-only candidate set; rebuild only when the set grows or a used external variable flips; splice nodes into the `@tailwind utilities` node and re-optimize.
- **Candidate sort ladder** — `candidate-sort-ladder`: bigint variant-position bitmask first, then property-order indexes, then most-properties, then alphabetical compare.
- **Design-system memo lattice** — `design-system-memo-lattice`: DefaultMap caches for parsed variants/candidates plus flags-keyed compiled-AST cache; substitution failures fail soft to "no rules"; rejected candidates feed a negative-result Set.
- **Variant application protocol** — `variant-application-protocol`: `applyVariant` returns `null` = whole candidate discarded; compound variants apply to an isolated `@slot` node; relative selectors are illegal as top-level arbitrary variants.
- **Theme namespace reset** — `theme-namespace-reset`: `initial` deletes keys, `-*: initial` clears namespaces minus protected sub-namespaces, `default` never beats existing user values.
- **Theme resolve var/inline** — `theme-resolve-var-inline`: INLINE emits raw values, otherwise escaped prefixed `var()` with a fallback only under REFERENCE; `markUsedVariable` returns first-use to gate rebuilds.
- **@theme ingestion** — `at-theme-ingestion`: all `@theme` blocks merge into one Theme; the first becomes the `:root, :host` output rule at that position; non-custom-property children hard-error.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
tailwindcss (MIT), v4.3.3, `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory project `tailwindcss` (FULL index 2026-08-25T20:02:24Z, 4569 nodes / 19796 edges; 9 parse-partial CSS-fixture/test files noted — none cited by these capsules; `src/compile.test.ts` absent at this pin, direct tests live in `index.test.ts` et al.).

## Full view (memory graph)
Revalidate `tailwindcss` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: candidate→AST compile with negative-result memoization, deterministic sort ladder, Theme fold/reset algebra, incremental add-only rebuild short-circuits. Adapt host-specific integration: scanner wiring (`crates/oxide` napi), import resolution, `@tailwindcss-{vite,postcss,browser}` drivers, compat plugin API. Omit product behavior: default theme content (`theme.css`), IntelliSense surfaces, upgrade codemods (`@tailwindcss-upgrade`).
