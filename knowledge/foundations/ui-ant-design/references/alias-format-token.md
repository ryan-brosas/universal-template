<!-- capsule-v2 -->
# Alias formatter — what precedence and special-case folding rules must the alias layer preserve?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** When porting the MapToken→AliasToken step, which merge order and conditional folds change observable component styles if gotten wrong?

## `formatToken` precedence + folds
**Path/Symbol:** `components/theme/util/alias.ts:formatToken` (lines 15–218).
**Signature:** `formatToken(derivativeToken: RawMergedToken): AliasToken` where `RawMergedToken = MapToken & OverrideToken & { override: Partial<AliasToken> }`.
**Data Shape:** Input is a derived map token plus an `override` bag; output is the developer-facing alias token (~200 keys).

### Decisive source
```ts
/** Seed (designer) > Derivative (designer) > Alias (developer). */
const { override, ...restToken } = derivativeToken;
const overrideTokens = { ...override };
Object.keys(seedToken).forEach((token) => {
  delete overrideTokens[token as keyof SeedToken];
});
const mergedToken = { ...restToken, ...overrideTokens };
// ...
if (mergedToken.motion === false) {
  const fastDuration = '0s';
  mergedToken.motionDurationFast = fastDuration;
  mergedToken.motionDurationMid = fastDuration;
  mergedToken.motionDurationSlow = fastDuration;
}
// ... alias object built from mergedToken remaps, then:
...overrideTokens,
```

**Flow:** strip `override` → delete seed-level keys from the override copy (seed overrides were already consumed by derivation; they must not re-win at alias stage) → fold overrides into `mergedToken` used for alias computation → apply folds → build alias remaps → spread `overrideTokens` one final time so alias-stage overrides win last.
**Invariant:** Precedence is three-tier, not linear: seed tokens beat everything at derivation time; developer alias overrides win only over alias defaults. The double handling of `overrideTokens` (deleted-seed-keys early, full spread late at line 214) IS the mechanism.

### Conditional folds a wrong port breaks
```ts
const lineWidthFocus = mergedToken.focusOutline === false ? 0 : mergedToken.lineWidth * 3;
// shadow algebra: base color alpha scales every shadow
const getShadowColor = (alpha: number) =>
  shadowBaseColor.clone().setA(shadowBaseAlpha * alpha).toRgbString();
```
- `motion === false` ⇒ all three motion durations `'0s'` (rendered-value test `token.test.tsx:237-251`).
- `focusOutline === false` ⇒ `lineWidthFocus === 0`, else `lineWidth * 3` (`token.test.tsx:253-257`).
- Shadows are computed from ONE `FastColor(colorShadow)` closure multiplying its **base alpha** — this is why dark theme shadows become `rgba(255,255,255,0.016)` without any per-theme shadow table (`token.test.tsx:324-339` pins light `0.08/0.16` vs dark `0.016/0.032`).
- Fixed screen ladder: XS 480 / SM 576 / MD 768 / LG 992 / XL 1200 / XXL 1600 / XXXL 1920; `screenXMax = next − 1`; `screenXMin = screenX`. These keys sit in `preserve` so css-var mode keeps them.
- Key alias remaps to preserve: `colorFillContent=FillSecondary`, `colorTextDisabled=colorTextQuaternary`, `controlItemBgActive=colorPrimaryBg`, `padding*/margin*` ladders mirror `size*`.

**Probe:** `components/theme/__tests__/token.test.tsx` lines 237–257 (motion/focusOutline folds), 296–322 (colorLink follows colorInfo even when colorPrimary changes), 324–339 (shadow adaptation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "formatToken alias override seed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier precedence with the seed-key deletion + late override re-spread; adopt motion-off/focus-off/shadow-alpha folds as behavior. Adapt the specific remap table to your design system's alias vocabulary. Omit antd's concrete default colors/sizes unless porting antd itself. Coverage: util/alias.ts `no_recorded_issue` (full read, 218 lines); no dedicated upstream spec file for alias.ts itself — probes above come from token.test.tsx.
