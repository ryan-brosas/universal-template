<!-- capsule-v2 -->
# Component-token externals — how does a component declare its own token set and derive defaults without hard-coding values?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter adding designer-tunable tokens to one component of a themed library needs the public/internal split and the derivation algebra that keeps dark/compact algorithms working for free.

## Public vs `@internal` split
**Path/Symbol:** `components/table/style/index.ts:ComponentToken` (lines 24–193) and `prepareComponentToken` (405–494).
**Signature:** `prepareComponentToken: GetDefaultToken<'Table'> = (token: FullToken<'Table'>) => Partial<ComponentToken>`.
**Data Shape:** ~29 public keys + 6 `/** @internal */` keys (`expandIconMarginTop`, `expandIconHalfInner`, `expandIconSize`, `expandIconScale`, `headerIconColor`, `headerIconHoverColor`). Graph-wide, `prepareComponentToken` matches **61 components** — it is the repo's per-component default-token convention (a few components like button/select keep theirs in `style/token.ts` instead).

### Decisive source
```ts
const colorFillSecondarySolid = new FastColor(colorFillSecondary)
  .onBackground(colorBgContainer).toHexString();
const baseColorAction = new FastColor(colorIcon);
...
headerBg: colorFillAlterSolid,
headerSortActiveBg: colorFillSecondarySolid,
rowSelectedBg: controlItemBgActive,
selectionColumnWidth: controlHeight,
stickyScrollBarBorderRadius: 100,
expandIconHalfInner: controlInteractiveSize / 2 - lineWidth,
expandIconSize: expandIconHalfInner * 2 + lineWidth * 3,
expandIconScale: controlInteractiveSize / expandIconSize,
headerIconColor: baseColorAction.clone()
  .setA(baseColorAction.a * opacityLoading).toRgbString(),
```

**Flow:** alias/seed token → pure derivations → component defaults. Three fill tokens are *solidified* against `colorBgContainer` via `FastColor.onBackground` (`colorFillAlter`→`headerBg`/`bodySortBg`/`footerBg`/`rowHoverBg`; `colorFillSecondary`→sort-active bgs; `colorFillContent`→hover bgs). Header icon colors scale the base alpha by `opacityLoading`. Expand-icon geometry is derived from `controlInteractiveSize`/`lineWidth`; `expandIconMarginTop` aligns the default font box to the small box: `(fontSize*lineHeight - lineWidth*3)/2 - ceil((fontSizeSM*1.4 - lineWidth*3)/2)`.
**Invariant:** NO hard-coded hexes or px in defaults — every value is an expression over incoming tokens, so switching algorithm (dark/compact) re-derives all component defaults automatically. Internal keys are computed here precisely so styles never re-derive them; users who set them anyway are outside the contract.

**Probe:** `components/table/__tests__/Table.virtual.test.tsx:130-151` sets `theme.components.Table.selectionColumnWidth = 200` and asserts `.ant-table-selection-col` renders `width: 200px` — a public ComponentToken flowing end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "prepareComponentToken Table headerBg expandIconSize", limit: 10 });
```

## Verdict
Adopt the two-tier ComponentToken shape (public documented keys + internal derived keys) and derivation-only defaults. Adapt `FastColor.onBackground` solidification to your color lib's equivalent composite-over-background op; the alpha-scaling trick (`setA(a * opacityLoading)`) is portable as-is. Omit bilingual `@desc` doc comments unless you generate token docs from them. Coverage: index.ts read in full (612 lines); coverage check `no_recorded_issue`.
