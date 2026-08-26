<!-- capsule-v2 -->
# Palette index ladder — what does palette[N] mean for every status color, and how do neutral ladders and radius clamps derive from two base colors?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter re-creating the token color system needs the exact index→role mapping and its per-color exceptions instead of guessing shades.

## Status-color ladder (`genColorMapToken`)
**Path/Symbol:** `components/theme/themes/shared/genColorMapToken.ts:genColorMapToken` (lines 12–120).
**Signature:** `(seed: SeedToken, { generateColorPalettes, generateNeutralColorPalettes }: PaletteGenerators): ColorMapToken`.
**Data Shape:** Six palettes (primary/success/warning/error/info/link) generated per theme via injected generators; output keys are `color<Role><Slot>`.

### Decisive source
```ts
colorPrimaryBg: primaryColors[1],
colorPrimaryBgHover: primaryColors[2],
colorPrimaryBorder: primaryColors[3],
colorPrimaryBorderHover: primaryColors[4],
colorPrimaryHover: primaryColors[5],
colorPrimary: primaryColors[6],
colorPrimaryActive: primaryColors[7],
colorPrimaryTextHover: primaryColors[8],
colorPrimaryText: primaryColors[9],
colorPrimaryTextActive: primaryColors[10],
```

**Flow:** seed status colors → per-color 10-step palette → fixed slot assignment. The SAME indices repeat for success/warning/error/info; exceptions only where noted.
**Invariant:** Index semantics are the contract: [1]=Bg, [2]=BgHover, [3]=Border, [4]=BorderHover, [5]=Hover, [6]=base, [7]=Active, [8]=TextHover, [9]=Text, [10]=TextActive. Dark swaps Hover/Active to [7]/[5] for preset colors only (see algorithm-composition).

### Exceptions and derived colors
```ts
const colorLink = seed.colorLink || seed.colorInfo;
const colorErrorBgFilledHover = new FastColor(errorColors[1])
  .mix(new FastColor(errorColors[3]), 50)
  .toHexString();
```
- Link falls back to info (`seed.colorLink || seed.colorInfo`) but must NOT follow colorPrimary — test pins `colorLink === colorInfo` even after recoloring primary (`token.test.tsx:296-322`).
- `colorErrorBgFilledHover = mix(error[1], error[3], 50%)`; `colorErrorBgActive = error[3]` while Border also takes `[3]`.
- Warning/Success/Info `Hover` slots take `[4]` (same as BorderHover) rather than `[5]` — read the file before assuming uniformity.
- Preset families get only two slots: `${colorKey}Hover=[5]`, `${colorKey}Active=[7]` (`PresetColors.forEach` block).
- Fixed constants: `colorBgMask = rgba(0,0,0,0.45)`, `colorWhite = '#fff'`.

### Neutral ladders (dark example)
```ts
colorText: getAlphaColor(colorTextBase, 0.85),
colorFill: getAlphaColor(colorTextBase, 0.18),
colorBgContainer: getSolidColor(colorBgBase, 8),
colorBgElevated: getSolidColor(colorBgBase, 12),
colorBorder: getSolidColor(colorBgBase, 26),
```
Dark text alpha steps 0.85/0.65/0.45/0.25; fill steps 0.18/0.12/0.08/0.04; surface solid steps container 8 / elevated 12 / layout 0 / spotlight & border 26 / borderSecondary 19. Light's `generateNeutralColorPalettes` lives in `themes/default/colors.ts` with the same signature — generators are injected so one shared consumer serves both themes.

**Probe:** `components/theme/__tests__/token.test.tsx:46-77` (seed `colorPrimary:'#ff0000'` → `colorPrimaryHover:'#ff3029'`; `orange:'#ff8800'` → `orange6:'#ff8800'`, `orange9:'#8c3d00'`) — pins both the derivation math and the dual key forms (`blue-6` and `blue6`, see default/index.ts reduce producing `` `${colorKey}-${i+1}` `` AND `` `${colorKey}${i+1}` ``).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "genColorMapToken generateNeutralColorPalettes presetColors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the index ladder + exception table as portable behavior; adopt generator injection (`PaletteGenerators`) so themes swap palette math without touching consumers. Adapt the concrete generation functions (@ant-design/colors/FastColor). Omit antd's specific default hues unless porting antd. Coverage: genColorMapToken.ts and dark/colors.ts read in full at pin, `no_recorded_issue`.
