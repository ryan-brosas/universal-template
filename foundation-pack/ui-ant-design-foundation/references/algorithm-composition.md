<!-- capsule-v2 -->
# Algorithm composition — how do dark/compact algorithms compose over the same seed, and where do they deliberately diverge?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter implementing theme algorithms must know the shared derivative contract and each algorithm's intentional deltas.

## Derivative function contract
**Path/Symbol:** `components/theme/themes/dark/index.ts:derivative` (11–62), `themes/compact/index.ts:derivative` (9–28), `themes/default/index.ts:derivative` (12–50).
**Signature:** `DerivativeFunc<SeedToken, MapToken> = (token: SeedToken, mapToken?: MapToken) => MapToken`.
**Data Shape:** `mapToken` is the user's partial map override; every algorithm starts `const mergedMapToken = mapToken ?? defaultAlgorithm(token)`.

### Decisive source (dark deltas)
```ts
const presetColorHoverActiveTokens = PresetColors.reduce<Record<string, string>>(
  (prev, colorKey) => {
    const colorBase = token[colorKey as keyof PresetColorType];
    if (colorBase) {
      const colorPalette = generateColorPalettes(colorBase);
      prev[`${colorKey}Hover`] = colorPalette[7];
      prev[`${colorKey}Active`] = colorPalette[5];
    }
    return prev;
  },
  {},
);
return {
  ...mergedMapToken,
  ...colorPalettes,
  ...colorMapToken,
  ...presetColorHoverActiveTokens,
  // https://github.com/ant-design/ant-design/issues/30524
  colorPrimaryBg: colorMapToken.colorPrimaryBorder,
  colorPrimaryBgHover: colorMapToken.colorPrimaryBorderHover,
};
```

**Flow:** default algorithm derives everything from seed → dark/compact re-derive only their slice and spread it OVER the merged default → last spreads win (`colorPrimaryBg` remap is final).
**Invariant:** Algorithms are pure functions of `(seed, mapToken?)`; composition `[darkAlgorithm, compactAlgorithm]` works because each is a MapToken→MapToken-ish fold cssinjs chains — test pins the composed result `colorPrimary '#1668dc'` (`token.test.tsx:280-293`).

### Deltas to preserve
1. **Dark inverts preset Hover/Active palette indices** — Hover=`palette[7]`, Active=`palette[5]`; the shared light ladder uses Hover=`[5]`, Active=`[7]` (`shared/genColorMapToken.ts`). Porting one index set for both themes breaks dark contrast.
2. **Dark remaps PrimaryBg→PrimaryBorder / BgHover→BorderHover** (issue 30524 comment in source).
3. **Dark palettes come from `generate(color, {theme:'dark'})`** and its neutral generator takes optional `shadowColor` defaulting `'rgba(255,255,255,0.2)'`; text/fill are alpha-over-textBase ladders (0.85/0.65/0.45/0.25; fills 0.18/0.12/0.08/0.04), surfaces are solid steps off bgBase (container 8, elevated 12, spotlight/border 26, borderSecondary 19).
4. **Compact demotes the size system:** `fontSize := merged.fontSizeSM`, `controlHeight := controlHeight - 4`, `compactSizeStep := sizeStep - 2`, sizes rebuilt as `sizeUnit * (step + n)` (`genCompactSizeMapToken.ts`) — note it receives `(mapToken ?? token)` but reads only seed fields `sizeUnit`/`sizeStep`.
5. **Default has a preset-palette fast path:** when a seed color equals `presetPrimaryColors[key]`, reuse `presetPalettes[key]` instead of regenerating; it also aliases `pink = magenta` once via module-state mutation for backwards compatibility.
6. **Radius clamps live in shared code** (`shared/genRadius.ts`): radiusLG +1 for 5–6, +2 for 6–16, cap 16; radiusSM plateaus 4/5/6/7/8; radiusXS 1 then 2; radiusOuter 4 then 6. Truth table pinned at `token.test.tsx:80-173` (e.g. base 16 → LG 16, SM 8, XS 2, Outer 6).

**Probe:** `components/theme/__tests__/token.test.tsx:280-293` (composed algorithms parity with hook), `80-173` (genRadius table).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "derivative darkAlgorithm compactAlgorithm genColorMapToken", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt `(seed, mapToken?) => MapToken` with the default-algorithm short-circuit and spread-order layering; adopt the dark index inversion and compact size demotion as named behavior. Adapt FastColor/@ant-design/colors generation internals. Omit the preset-palette mutation hack unless you carry antd's legacy `pink` alias. Coverage: all cited files read directly at pin; `no_recorded_issue` on the checked batch.
