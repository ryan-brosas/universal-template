<!-- capsule-v2 -->
# Round vs interpolate conflict — what happens when a scale config sets BOTH, and how does round work on scales without .round()?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** Why does `round:true` swap the INTERPOLATOR on continuous scales, and which key wins when both are set?

## Warn-and-prefer-interpolate; round = interpolateRound
**Path/Symbol:** `packages/visx-scale/src/operators/round.ts:applyRound` (:5–27).
**Signature:** `applyRound(scale: D3Scale, config: ScaleConfigWithoutType): void`.
**Data Shape:** three mutually exclusive arms: (1) both keys set → warn + skip; (2) scale has `.round()` (point/band) → call it; (3) continuous scale → `scale.interpolate(interpolateRound)`.

### Decisive source
```ts
if (config.round && 'interpolate' in config && typeof config.interpolate !== 'undefined') {
  console.warn(
    `[visx/scale/applyRound] ignoring round: scale config contains round and interpolate. only applying interpolate. config:`,
    config,
  );
} else if ('round' in scale) {
  // for point and band scales
  scale.round(config.round);
} else if ('interpolate' in scale && config.round) {
  // setting config.round = true is actually setting interpolator to interpolateRound
  // as these scales do not have scale.round() function
  scale.interpolate(interpolateRound as unknown as InterpolatorFactory<Output, Output>);
}
```

**Flow:** conflict check FIRST (explicit interpolator always wins, round is dropped with a console.warn naming the config) → discrete scales get real rounding of band positions → continuous scales emulate rounding by replacing the range interpolator with d3's `interpolateRound`.
**Invariant:** the double-cast (`as unknown as InterpolatorFactory`) is required because interpolateRound's signature is narrower than the factory type — porters who "fix" the cast into a direct assignment hit TS errors. Silent round application when an explicit interpolator exists would discard user color/gradient interpolators — hence warn-and-skip.
**Probe:** `packages/visx-scale/test/updateScale.test.ts` (round cases); warning text pinned by string in test suite (`grep -rn "ignoring round" packages/visx-scale` → src/operators/round.ts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "applyRound interpolateRound", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI twin resolves `packages/visx-scale/src/operators/round.ts :5-27`; verified live this pass.)

## Verdict
Adopt the three-arm ladder verbatim; adapt the console.warn to your logger; omit nothing — behavior is fully test-pinned.
