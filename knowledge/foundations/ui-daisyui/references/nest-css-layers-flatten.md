<!-- capsule-v2 -->
# CSS-object layer flattening — how do authored `@layer` blocks inside a JS styles object survive handoff to Tailwind's addComponents?

**Source:** daisyUI MIT `master@c6e1800bc15ab0287b8c2b802c126ccee6361beb`; Codebase Memory `ui-daisyui`. **Question:** When component sources express cascade-layer intent as object keys like `"@layer daisyui.l1.l2"`, how do I hoist the real selectors out and re-wrap them so Tailwind emits valid CSS?

## Layer-block hoist with at-rule accumulation
**Path/Symbol:** `packages/daisyui/functions/nestCssLayers.js:1-43` (`nestCssLayers`, `moveLayerRules`, `appendRule`, `wrapWithAtRules`).
**Signature:** `nestCssLayers(styles: object) → object`; inner `moveLayerRules(styles, layerValue, atRules[])`.
**Data Shape:** input is a Tailwind-style CSS object whose keys are selectors, at-rules, or `@layer a.b.c` names; values are rule objects or arrays of them. Output keeps selector/at-rule keys but each value is either the original rule, an array of merged rules, or `{ "@layer …": { … } }`-wrapped content.

### Decisive source
```js
const wrapWithAtRules = (rule, atRules) =>
  atRules.reduceRight((wrappedRule, atRule) => ({ [atRule]: wrappedRule }), rule)

const moveLayerRules = (styles, layerValue, atRules) => {
  const layerBlocks = Array.isArray(layerValue) ? layerValue : [layerValue]
  for (const layerBlock of layerBlocks) {
    for (const [key, value] of Object.entries(layerBlock)) {
      if (key.startsWith("@")) {
        moveLayerRules(styles, value, [...atRules, key])
        continue
      }
      appendRule(styles, key, wrapWithAtRules(value, atRules))
    }
  }
}
```

**Flow:** top-level keys starting with `@layer ` are removed as keys and their contents walked → nested at-rules (e.g. `@media (hover: hover)`) accumulate onto the at-rule chain recursively → every concrete selector is re-inserted at top level with its value wrapped back through the accumulated chain via `reduceRight` (innermost at-rule ends up innermost in the output) → non-layer keys pass through `appendRule` untouched except for merge behavior.
**Invariant:** duplicate selectors must merge by appending to an array (`[currentRule, rule]`), never overwrite — the test pins `.btn` ending as `[{ display: "inline-flex" }, { "@layer daisyui.l1": { color: "red" } }]`; `@keyframes` blocks pass through unmodified; media queries inside a layer end up *inside* the layer wrapper, not siblings of it.
**Probe:** `packages/daisyui/functions/nestCssLayers.test.js:4-39` ("moves top-level CSS layers under their selectors") — full input/output equality including array merge and keyframes passthrough; executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ui-daisyui", qualified_name: "ui-daisyui.packages.daisyui.functions.nestCssLayers.nestCssLayers" });
```
Executed this pass indirectly via the graph row (`nestCssLayers.js 30-43`) plus direct full-file read; callers confirmed from `index.js:39/47`.

## Verdict
Adopt hoist-and-rewrap with array merging as a pure contract — it is what lets authors write plain layered CSS while the plugin API receives flat selectors. Adapt layer naming (`daisyui.l1…` belongs to daisyUI's specificity ladder). Omit nothing else; the function has no host coupling beyond Tailwind's CSS-object convention.
