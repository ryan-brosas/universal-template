<!-- capsule-v2 -->
# Zero operator on descending domains — how do you extend a scale domain to include 0 without breaking reversed axes?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** `domain.push(0)` + sort destroys a descending (reversed) domain — what is the correct zero-extension?

## Normalize direction, extend, restore direction
**Path/Symbol:** `packages/visx-scale/src/operators/zero.ts:applyZero` (:5–21).
**Signature:** `applyZero(scale: D3Scale, config: ScaleConfigWithoutType): void`.
**Data Shape:** reads `scale.domain()` as `number[]` pair `[a, b]`; writes back only when `config.zero === true` (strict equality — truthy strings don't trigger).

### Decisive source
```ts
if ('zero' in config && config.zero === true) {
  const domain = scale.domain() as number[];
  const [a, b] = domain;
  const isDescending = b < a;
  const [min, max] = isDescending ? [b, a] : [a, b];
  const domainWithZero = [Math.min(0, min), Math.max(0, max)];
  scale.domain(isDescending ? domainWithZero.reverse() : domainWithZero);
}
```

**Flow:** detect descending via `b < a` → normalize to `[min,max]` → widen with `Math.min/Math.max` against 0 → if input was descending, reverse the widened pair before writing.
**Invariant:** the OUTPUT orientation must match the INPUT orientation. A naive `[Math.min(0,d0), Math.max(0,d1)]` silently un-reverses descending domains and flips the rendered axis. The same min/max-then-reorient pattern reappears independently in `visx-react-spring/src/spring-configs/useLineTransitionConfig.ts:67-71` (`isDescending = b < a; [scaleMin,scaleMax] = isDescending ? [b,a] : [a,b]`) — it is the repo-wide convention for range-relative math on possibly-inverted scales.
**Probe:** `packages/visx-scale/test/scaleLinear.test.ts :94-103` — four-domain table incl. the two descending cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "applyZero", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-scale/src/operators/zero.ts :5-21
```

## Verdict
Adopt whole (12 lines of pure logic); adapt nothing; omit d3 wrapper typing. Direct test pins all four orientations — no coverage caveat.
