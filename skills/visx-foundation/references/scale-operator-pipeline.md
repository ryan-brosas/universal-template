<!-- capsule-v2 -->
# Scale operator pipeline — in what ORDER do scale config keys apply, and why does it matter?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** When a porter applies `{domain, nice, zero, range, reverse, round, interpolate}` to a d3 scale, which key must win when they interact (nice vs zero, round vs interpolate, range vs reverse)?

## Operator selection is order-of-execution, not object order
**Path/Symbol:** `packages/visx-scale/src/operators/scaleOperator.ts:scaleOperator` (:66–86) + `ALL_OPERATORS` (:22–44).
**Signature:** `scaleOperator<T extends ScaleType>(...ops: OperatorType[]) => (scale, config?) => scale`.
**Data Shape:** `ops` are names from the fixed 14-entry `ALL_OPERATORS` tuple; a per-factory closure filters them into `selectedOps` preserving CANONICAL order regardless of call-site argument order.

### Decisive source
```ts
export const ALL_OPERATORS = [
  // domain => nice => zero
  'domain', 'nice', 'zero',
  // interpolate before round
  'interpolate', 'round',
  // set range then reverse
  'range', 'reverse',
  // Order does not matter for these operators
  'align', 'base', 'clamp', 'constant', 'exponent', 'padding', 'unknown',
] as const;
...
const selectedOps = ALL_OPERATORS.filter((o) => selection.has(o));
```

**Flow:** factory (`createLinearScale` etc.) closes over its op subset → apply time: for each selected op in canonical order read `config[key]` if present, mutate the scale instance, return the same instance. Each operator guards with feature detection (`'clamp' in scale && 'clamp' in config`) so one generic operator table serves all 14 scale types.
**Invariant:** `zero` runs AFTER `domain`+`nice` so zero-extension sees the niced domain; `interpolate` runs BEFORE `round` because `applyRound` only swaps in `interpolateRound` when no explicit interpolator was configured; `reverse` runs AFTER `range` because it flips whatever range was just set. Reorder any of these and configs silently produce different domains/ranges — this array IS the contract.
**Probe:** `packages/visx-scale/test/scaleLinear.test.ts` — `scaleLinear({ domain: [1, -2], zero: true }).domain()` stays `[1, -2]` while `[1,2]→[0,2]`, `[-2,-1]→[-2,0]`, `[-2,3]` unchanged (:94–103); also `updateScale.test.ts :16-18` pins `reverse` flipping a custom range.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "scaleOperator ALL_OPERATORS", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-scale/src/operators/scaleOperator.ts :66-86
```

## Verdict
Adopt the canonical-order operator pipeline + feature-detection guards verbatim (pure logic over d3 scales); adapt `@visx/vendor/d3-scale` imports to your host d3; omit the 14 per-type overload signatures in `createScale.ts`/`updateScale.ts` (typing sugar, ~150 lines each). Coverage caveat: barrel `index.ts` files are parse_partial-flagged; every cited operator file is clean (`no_recorded_issue`, generation_matches=true).
