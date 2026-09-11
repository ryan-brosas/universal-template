<!-- capsule-v2 -->
# combineNiceTicks — when does recharts apply its own tick rounding at all?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** Given the `niceTicks` axis setting, domain shape, and resolved scale type, which generator (if any) runs and with which mode?

## Mode dispatch funnel
**Path/Symbol:** `src/state/selectors/axisSelectors.ts:combineNiceTicks` (:1256-1309).
**Signature:** `combineNiceTicks(axisDomain, axisSettings: RenderableAxisSettings, realScaleType?: string) => ReadonlyArray<number> | undefined`.
**Data Shape:** Pure combiner (no state access); returns undefined whenever rounding is off/unapplicable — callers must treat that as "let d3 ticks decide".

### Decisive source
```ts
const { niceTicks } = axisSettings;
if (niceTicks === 'none') {
  return undefined;
}
const domainDefinition: AxisDomain = getDomainDefinition(axisSettings);
const hasDomainAutoKeyword =
  Array.isArray(domainDefinition) && (domainDefinition[0] === 'auto' || domainDefinition[1] === 'auto');

if ((niceTicks === 'snap125' || niceTicks === 'adaptive') && axisSettings != null && axisSettings.tickCount
     && isWellFormedNumberDomain(axisDomain)) {
  if (hasDomainAutoKeyword) {
    return getNiceTickValues(axisDomain, axisSettings.tickCount, axisSettings.allowDecimals, niceTicks);
  }
  if (axisSettings.type === 'number') {
    return getTickValuesFixedDomain(axisDomain as NumberDomain, axisSettings.tickCount, axisSettings.allowDecimals, niceTicks);
  }
}
if (niceTicks === 'auto' && realScaleType === 'linear' && axisSettings != null && axisSettings.tickCount) {
  if (hasDomainAutoKeyword && isWellFormedNumberDomain(axisDomain)) {
    return getNiceTickValues(axisDomain, axisSettings.tickCount, axisSettings.allowDecimals, 'adaptive');
  }
  if (axisSettings.type === 'number' && isWellFormedNumberDomain(axisDomain)) {
    return getTickValuesFixedDomain(axisDomain as NumberDomain, axisSettings.tickCount, axisSettings.allowDecimals, 'adaptive');
  }
}
return undefined;
```

**Flow:** explicit opt-out first → detect the `'auto'` keyword from the USER's domain definition (not the evaluated domain) → explicit modes ('adaptive'/'snap125') run on well-formed numeric domains choosing extension-vs-fixed by the keyword → legacy `'auto'` additionally requires the RESOLVED scale to be linear and always uses the adaptive step internally.
**Invariant:** The auto-keyword check reads the user's declared domain (`getDomainDefinition(axisSettings)`), while the numeric-domain checks read the EVALUATED `axisDomain` argument — conflating the two is the classic porting error. Category axes with fixed domains get nothing in 'auto' mode (pinned by test).
**Probe:** `test/state/selectors/combineNiceTicks.spec.ts` ("uses adaptive mode for auto + auto domain": `[12,468], type:'number', niceTicks:'auto', tickCount:5, domain:['auto','auto']` → `[0,150,300,450,600]`; "returns undefined for unsupported scale types" pins `niceTicks:'auto', realScaleType='time'` → undefined).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "combineNiceTicks", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified line-exact :1256-1309; trace_path confirms callees {getDomainDefinition, isWellFormedNumberDomain, calculateStep, getNiceTickValues, getTickOfSingleValue, getTickValuesFixedDomain, getValidInterval, rangeStep, getDigitCount}.

## Verdict
Adopt the three-arm dispatch exactly; adapt the selector wrapper (upstream wraps this in `createSelector([selectAxisDomain, selectRenderableAxisSettings, selectRealScaleType])`); omit redux plumbing. Upstream direct tests pin every arm including both undefined paths.
