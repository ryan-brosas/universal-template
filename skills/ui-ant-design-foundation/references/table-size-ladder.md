<!-- capsule-v2 -->
# Table size ladder — how do `small`/`medium` density variants override the base styles and compensate dependent margins?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter implementing density variants over a token system needs the size-override builder and the compensating-margin algebra that keeps overlays aligned.

## Size builder
**Path/Symbol:** `components/table/style/size.ts:genSizeStyle` (7–72), inner `getSizeStyle` (9–55).
**Signature:** `getSizeStyle(size: 'small'|'medium', paddingVertical: number, paddingHorizontal: number, fontSize: number) => CSSObject`.
**Data Shape:** two instantiations — medium ← `tablePadding*Middle`/`cellFontSizeMD`, small ← `tablePadding*Small`/`cellFontSizeSM`; both spread into one `${componentCls}-wrapper` scope.

### Decisive source
```ts
[`${componentCls}${componentCls}-${size}`]: {
  fontSize,
  [`${componentCls}-title, ${componentCls}-footer, ${componentCls}-cell,
    ${componentCls}-thead > tr > th, ...`]: {
    padding: `${unit(paddingVertical)} ${unit(paddingHorizontal)}`,
  },
  [`${componentCls}-filter-trigger`]: {
    marginInlineEnd: unit(calc(paddingHorizontal).div(2).mul(-1).equal()),
  },
  [`${componentCls}-expanded-row-fixed`]: {
    margin: `${unit(calc(paddingVertical).mul(-1).equal())}
             ${unit(calc(paddingHorizontal).mul(-1).equal())}`,
  },
  [`${componentCls}-selection-extra`]: {
    paddingInlineStart: unit(calc(paddingHorizontal).div(4).equal()), // #35167
  },
},
```

**Flow:** base cell padding comes from the default size (`cellPaddingBlock/Inline`); each size class re-declares padding+fontSize, then NEGATIVELY compensates every element that must bleed to the cell edge: filter trigger pulls back half the horizontal padding, expanded-row-fixed bleeds by exactly `-paddingV -paddingH`, nested-table margins reuse `tableExpandColumnWidth - paddingH`.
**Invariant:** compensation margins are always derived from the SAME size's padding tokens via `calc()` — never independent constants; change a padding token and every overlay stays glued. Selector form is `${componentCls}${componentCls}-${size}` (class adjacency, same specificity as base) so variant rules win by source order inside one generated stylesheet.

**Probe:** `components/table/__tests__/Table.test.tsx` size demos are snapshot-pinned (`demo.test.ts.snap` renders `-small`/`-medium` classes); token inputs pinned by `Table.virtual.test.tsx:130-151` for the analogous width-token path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "genSizeStyle getSizeStyle small medium tablePadding", limit: 10 });
```

## Verdict
Adopt the parametrized size-builder + calc-derived negative compensations. Adapt selector strategy if your style engine orders differently. Omit antd's specific issue-linked quirks unless you inherit them (#35167 selection-extra quarter-padding). Coverage: size.ts read in full (74 lines), `no_recorded_issue`.
