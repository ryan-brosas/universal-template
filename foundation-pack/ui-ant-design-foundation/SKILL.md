---
name: ui-ant-design-foundation
description: "Use when porting Ant Design's design-token kernel AND its component-consumer plane: seed→derivative→alias token ladder, per-component algorithm recursion, sync getDesignToken parity, dark/compact algorithm deltas, palette index semantics, radius clamps, CSS-var naming/unitless wiring for cssinjs-style style hooks, plus the Table-proven consumption contracts — prepareComponentToken externals, genStyleHooks registration with mergeToken renaming, fixed/RTL shadow machinery, size ladders, nested-border CSS-var protocol, and dual style/layout token consumption."
disable-model-invocation: true
---

# Ant Design (ui-ant-design): design-token kernel contracts

## Use this for
Use when porting or re-implementing a theme/token system shaped like antd's `components/theme`: the `useToken` context path with its cache salt and override/component recursion, the React-free `getDesignToken` sync path that must stay output-equal to the hook, the alias formatter's precedence and special-case folding (motion off, focus outline off, screen ladder, shadow alpha algebra), dark/compact algorithm composition over `(seedToken, mapToken?)`, palette-index semantics shared by all status colors, piecewise radius clamps, and the `--ant-<component>-*` CSS-variable naming plus unitless/ignore/preserve classes that style-hook factories consume. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/token-computed-ladder.md` — how runtime tokens are computed, cached, and how per-component themes recurse.
- `references/designtoken-sync-parity.md` — computing tokens outside React while staying equal to the hook path.
- `references/alias-format-token.md` — precedence contract and special-case folding in the alias layer.
- `references/algorithm-composition.md` — derivative signature, mapToken short-circuit, dark/compact deltas.
- `references/palette-index-ladder.md` — what palette[1..10] means for every status color; neutral ladders; radius clamps.
- `references/cssvar-naming-contract.md` — CSS-var naming, fallbacks, unitless classes, reset-style injection.
- `references/component-token-externals.md` — public vs `@internal` component tokens; derivation-only defaults algebra (Table-proven, repo-wide ×61 convention).
- `references/style-hook-registration.md` — genStyleHooks registration, mergeToken `table*` second alias layer, per-component unitless/reset options.
- `references/fixed-shadow-contract.md` — fixed-column two-plane shadows, z-index CSS-var algebra, rc-table boundary.
- `references/rtl-shadow-mirror.md` — direction layer swaps shadow sides without regenerating primitives.
- `references/table-size-ladder.md` — small/medium density builder with calc-derived compensating margins.
- `references/nested-border-cssvar.md` — publish/consume/reset custom-property protocol for self-nesting components.
- `references/token-to-layout-consumption.md` — one ComponentToken feeding both CSS and JS layout defaults; props win by spread order.

## Capsule map
- **Token computation** — `token-computed-ladder`: `useCacheToken(theme, [defaultSeed, rootToken], {salt: version-hashed, override, getComputedToken, cssVar})`; `getComputedToken` derives via `theme.getDerivativeToken`, applies `override`, formats, then recurses the whole pipeline for component entries carrying their own `theme`.
- **Sync parity** — `designtoken-sync-parity`: `getDesignToken(config)` calls cssinjs's own `getComputedToken` with `formatToken` injected as a formatter; tests pin `toEqual(hookToken)` across default/custom/custom-algorithm configs.
- **Alias layer** — `alias-format-token`: "Seed > Derivative > Alias" precedence; seed keys deleted from overrides before the final alias spread; motion-off zeroes durations; focusOutline-off zeroes lineWidthFocus; fixed screen ladder; shadow colors scale the base color's alpha.
- **Algorithms** — `algorithm-composition`: `DerivativeFunc(seedToken, mapToken?)` with `mapToken ?? defaultAlgorithm(token)` short-circuit; dark inverts preset Hover/Active indices and remaps PrimaryBg to Border; compact rebuilds sizes from `sizeStep-2` and demotes fontSize to fontSizeSM.
- **Palettes** — `palette-index-ladder`: [1]=Bg … [6]=base … [10]=TextActive; dark neutral alpha ladders and solid-color surface steps; genRadius piecewise clamp table.
- **CSS vars** — `cssvar-naming-contract`: `genCssVar(antCls, component)` builds dot-stripped `--ant-<component>-` prefixes; one shared unitless map feeds both token computation and the style-hook factory.
- **Component-token externals** — `component-token-externals`: public ComponentToken keys + `@internal` derived keys; `prepareComponentToken` defaults are 100% token expressions (FastColor `onBackground` solidification, alpha×`opacityLoading` icon colors, expand-icon geometry) — repo-wide convention across ~61 components.
- **Style-hook registration** — `style-hook-registration`: `genStyleHooks('Table', fn, prepareComponentToken, {resetFont:false, unitless:{expandIconScale:true}})`; `mergeToken` renames component tokens into a `table*` second alias layer; constants folded at one site; duplicate-generator quirk documented.
- **Fixed shadows** — `fixed-shadow-contract`: single color input (`colorSplit`), cell `::after` + container edge planes, `-has-fix-*` suppression, z-index from rc-table-emitted `--z-offset-reverse`/`--columns-count` vars; geometry deliberately NOT tokens.
- **RTL mirror** — `rtl-shadow-mirror`: direction layer re-imports the same shadow tuple and swaps left/right application; primitives stay direction-free.
- **Size ladder** — `table-size-ladder`: parametrized small/medium builder over `cellPadding*MD/SM`; overlays compensated by calc-derived negative margins from the SAME size's tokens.
- **Nested borders** — `nested-border-cssvar`: publish (`--ant-table-nested-border-top`) → consume-with-fallback → reset-to-0-in-nested-scope protocol via genCssVar; plus bordered-plane fix dedups (#56287).
- **Dual consumption** — `token-to-layout-consumption`: `{columnWidth: token.Table?.selectionColumnWidth, ...props}` feeds JS layout while styles read the same token; test pins 200px→50px override chain.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Ant Design (MIT), `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory project `ui-ant-design` (24,948 nodes / 79,593 edges, FULL mode, generation 2026-08-25T19:59:19Z; skipped=0; parse_partial ×6 confined to dumi demos/changelogs — none cited). Pass 1: components/theme kernel (6 capsules). Pass 2: components/table token-consumer style plane (7 capsules); pin unchanged, zero index drift verified.

## Full view (memory graph)
Revalidate `ui-ant-design` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note: hook seams resolve through USAGE edges (`useToken` has 68 in-degree but 0 CALLS callers) — trace_path inbound returns empty for hooks, so confirm consumers with search_graph degree columns instead. The full initial index can outrun the MCP call timeout; if list_projects times out right after indexing, wait and re-poll before assuming failure.

## Boundaries
Adopt the pure contracts (token ladder order, algorithm signatures, palette indices, radius clamps, var naming); adapt host-specific integration (React contexts, cssinjs cache internals like useCacheToken/createTheme, FastColor arithmetic) to your stack's equivalents; omit antd product behavior (dumi docs site, demo fixtures, changelog tooling) — they consume the captured contracts.
