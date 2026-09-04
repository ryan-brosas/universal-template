<!-- capsule-v2 -->
# rechartsScaleFactory + combineRealScaleType/combineConfiguredScale — how do string scale names become immutable scale objects?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** What does the internal scale wrapper add over d3, why is immutability enforced, and how do 'auto'/unknown/function scales resolve?

## Scale resolution + immutable wrapper
**Path/Symbol:** `src/util/scale/RechartsScale.ts:rechartsScaleFactory` (:86-130); `src/state/selectors/combiners/combineRealScaleType.ts:combineRealScaleType` (:14-43); `src/state/selectors/combiners/combineConfiguredScale.ts:combineConfiguredScaleInternal` (:55-77).
**Signature:** `rechartsScaleFactory(d3Scale?: CustomScaleDefinition) => RechartsScale | undefined`; `combineRealScaleType(axisConfig?, hasBar, chartType) => RechartsScaleType | undefined`; `combineConfiguredScaleInternal(scale, axisDomain, axisRange) => CustomScaleDefinition | undefined`.
**Data Shape:** `RechartsScale` = `{ domain(), range(), rangeMin(), rangeMax(), isInRange(n), bandwidth?(), ticks?(count), map(input, {position}) }` — note `map`, NOT d3's call-as-function; range is normalized to `[min,max]` at wrap time.

### Decisive source
```ts
// combineRealScaleType — 'auto' resolution:
if (scale === 'auto') {
  if (type === 'category' && chartType &&
      (chartType.indexOf('LineChart') >= 0 || chartType.indexOf('AreaChart') >= 0 ||
       (chartType.indexOf('ComposedChart') >= 0 && !hasBar))) {
    return 'point';
  }
  if (type === 'category') {
    return 'band';
  }
  return 'linear';
}
if (typeof scale === 'string') {
  return isSupportedScaleName(scale) ? scale : 'point'; // unknown strings silently become point
}
return undefined; // function scales bypass this resolver
```
```ts
if (typeof scale === 'function') {
  return scale.copy().domain(axisDomain).range(axisRange); // copy() BEFORE mutating: user's scale untouched
}
```
```ts
// wrapper: map() with band positioning
map: (input, options?) => {
  let baseValue = d3Scale(input);
  if (baseValue == null) return undefined;
  if (d3Scale.bandwidth && options?.position) {
    const bandWidth = d3Scale.bandwidth();
    switch (options.position) {
      case 'middle': baseValue += bandWidth / 2; break;
      case 'end': baseValue += bandWidth; break;
      default: break;
    }
  }
  return baseValue;
},
```

**Flow:** user prop → real type ('auto' resolves by chart kind + bar presence; unknown names degrade to 'point') → factory instantiates d3 scale (short or `scaleXxx` name; non-function exports like the `scaleImplicit` Symbol return undefined) → configured with `.copy()` first for function scales → wrapped immutable where every accessor closes over frozen method refs and callers use `.map()`.
**Invariant:** The wrapper exists because "mutating the scale in place would not trigger re-renders" (in-source comment); it also NORMALIZES descending ranges (`rangeMin/rangeMax` via Math.min/max) and centralizes band-position math so graphical items never hand-add bandwidth. Function-scale inputs are copied, never mutated — a porter who configures the user's scale directly breaks external state.
**Probe:** `test/state/selectors/combiners/combineRealScaleType.spec.ts` ("returns point for auto + category in LineChart/AreaChart"; "returns point for auto + category in ComposedChart without bars, but band with bars"); `test/state/selectors/combiners/combineConfiguredScale.spec.ts` ("returns undefined for a name that resolves to a non-function d3 export").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "rechartsScaleFactory", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified line-exact :86-130.

## Verdict
Adopt the three-stage pipeline and the copy-before-configure rule; adapt the d3 import path (upstream uses victory-vendor); omit `CartesianScaleHelper` unless you port paired-axis mapping.
