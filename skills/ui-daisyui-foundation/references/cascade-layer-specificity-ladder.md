<!-- capsule-v2 -->
# Cascade-layer specificity ladder — how does daisyUI control override precedence across its own rules without `!important`?

**Source:** daisyUI MIT `master@c6e1800bc15ab0287b8c2b802c126ccee6361beb`; Codebase Memory `ui-daisyui`. **Question:** When two of my component rules match the same element (base shape vs state variant), how do I guarantee which one wins using cascade layers instead of specificity wars?

## Layer-nesting depth as precedence tier
**Path/Symbol:** `packages/daisyui/src/components/button.css:11-75` and the repo-wide authoring convention (`status.css`, `toggle.css`, `tab.css`, …); deepest nesting `@layer daisyui.l1.l2.l3`, shallowest meaningful `@layer daisyui`.
**Signature:** CSS authoring contract, not a function: `.selector { @layer daisyui.l1.l2.l3 { … } }`.
**Data Shape:** every component rule declares which tier it belongs to; tiers are nested layer names so deeper = later in layer order = wins among equal-specificity selectors. Theme tokens arrive as vars with fallbacks; per-component private vars act as override hooks.

### Decisive source (button.css, parse-partial file read directly)
```css
.btn {
  @layer daisyui.l1.l2.l3 {
    --btn-bg: var(--btn-color, var(--color-base-200));
    --btn-border: color-mix(in oklab, var(--btn-color, var(--color-base-200)), #000 calc(var(--depth) * 5%));
    background-color: var(--btn-bg);
    ...
    &:where(:checked:not(.filter [type="radio"].btn)) {
      --btn-color: var(--color-primary);
      --btn-fg: var(--color-primary-content);
    }
  }

  @layer daisyui.l1 {
    @media (hover: hover) { &:hover { ... } }
  }
```

**Flow:** base component shape sits in `daisyui.l1.l2.l3` (deepest → highest precedence within the daisyui tree) → hover/state blocks that must lose to the base sit in shallower `daisyui.l1` or `daisyui.l1.l2` → variants don't re-declare properties; they set a private hook var (`--btn-color`) that the deep block consumes via `var(--btn-color, fallback)` → depth-driven visual effects scale from the theme token: `calc(var(--depth) * N%)` inside `color-mix(in oklab, …)` → utility `join.css` uses a fourth tier `.l1.l2.l3.l4` when it must beat all components.
**Invariant:** precedence differences come only from layer-nesting depth (and `:where()` wrappers keeping base selectors at zero specificity), never from `!important`; any new rule must pick the tier matching its intended win/lose relationship, because equal-depth conflicts fall back to source order.
**Probe:** no dedicated upstream unit test pins the ladder itself — it is enforced by compiled-output parity in the docs/build. Coverage caveat recorded: cited CSS files are parse-partial in the graph; ranges were read directly at pin. Deterministic anchor: `functions/generateRawStyles.test.js:53-78` proves layered sources survive the build pipeline structurally.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-daisyui", query: "component layer l1 l2 l3 button", limit: 10 });
```
Executed this pass as a grep census over `src/components/*.css` (250 matches for `@layer daisyui` patterns) plus direct reads of `button.css:1-75`, confirming the tier vocabulary (`l1`, `l1.l2`, `l1.l2.l3`, and `l1.l2.l3.l4` in join.css).

## Verdict
Adopt "layer-nesting depth = precedence tier + private hook vars for variant overrides" as a portable design-system contract. Adapt the layer namespace and token names. Omit daisyUI's concrete components; note the caveat that this invariant is by-convention with no dedicated upstream test.
