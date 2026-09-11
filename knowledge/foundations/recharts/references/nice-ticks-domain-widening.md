<!-- capsule-v2 -->
# combineAxisDomainWithNiceTicks — how do nice ticks GROW the rendered domain, and which axis is exempt?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** Where do the extra tick values past the data range become part of the axis domain itself?

## Domain-widening combiner
**Path/Symbol:** `src/state/selectors/axisSelectors.ts:combineAxisDomainWithNiceTicks` (:1321-1347).
**Signature:** `combineAxisDomainWithNiceTicks(axisSettings: BaseCartesianAxis, domain, niceTicks?: ReadonlyArray<number>, axisType: RenderableAxisType) => NumberDomain | CategoricalDomain | undefined`.
**Data Shape:** Pure function; returns a NEW two-number domain when widening applies, else the input domain unchanged.

### Decisive source
```ts
if (
  /*
   * Angle axis for some reason uses nice ticks when rendering axis tick labels,
   * but doesn't use nice ticks for extending domain like all the other axes do.
   */
  axisType !== 'angleAxis' &&
  axisSettings?.type === 'number' &&
  isWellFormedNumberDomain(domain) &&
  Array.isArray(niceTicks) &&
  niceTicks.length > 0
) {
  const minFromDomain = domain[0];
  const minFromTicks = niceTicks[0] ?? 0;
  const maxFromDomain = domain[1];
  const maxFromTicks = niceTicks[niceTicks.length - 1] ?? 0;
  return [Math.min(minFromDomain, minFromTicks), Math.max(maxFromDomain, maxFromTicks)];
}
return domain;
```

**Flow:** guard on axis kind + numeric type + well-formed numeric domain + non-empty niceTicks → widen symmetric-min/max between evaluated domain and tick extremes (ticks may exceed the domain per `getNiceTickValues`) → everything else passes through untouched.
**Invariant:** The angle-axis exemption is documented upstream as unexplained legacy ("not really sure why?") — preserve it anyway; removing it changes RadarChart/PieChart rendering. Widening uses ONLY the first/last tick, not each tick.
**Probe:** `grep -n "axisType !== 'angleAxis'" src/state/selectors/axisSelectors.ts` → exactly 1 hit at :1334; consumer chain: `selectNiceTicks → combineAxisDomainWithNiceTicks → selectAxisDomainIncludingNiceTicks → selectCheckedAxisDomain → selectConfiguredScale` (each `createSelector`-wrapped in the same file :1311-1357, :1596+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "combineAxisDomainWithNiceTicks", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified line-exact :1321-1347.

## Verdict
Adopt the widen-only-if rules and keep the angle-axis carve-out with its comment; adapt if your chart has no polar family; omit nothing. Behavior is pinned indirectly by polar specs (`test/polar/*` reference niceTicks) — no dedicated unit test exists for this combiner; treat the grep pin as the anchor.
