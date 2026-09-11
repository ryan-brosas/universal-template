<!-- capsule-v2 -->
# Style-hook registration — how does a component register its styles, rename tokens into a second alias layer, and extend the unitless set?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter wiring one component's style module into the shared token factory needs the registration signature, the token-renaming layer, and the option surface.

## Registration call
**Path/Symbol:** `components/table/style/index.ts:495-612` (default export); `components/theme/internal.ts` (whole, 58 lines); runtime consumer `InternalTable.tsx:344-345`.
**Signature:** `genStyleHooks('Table', (token: FullToken<'Table'>) => CSSObject[], prepareComponentToken, { resetFont: false, unitless: { expandIconScale: true } })`.
**Data Shape:** 17 generator results aggregated; ~35 `table*` renamed keys via `mergeToken`; `theme/internal.ts` re-exports `genStyleHooks/genComponentStyleHook/genSubStyleComponent` (from local `util/genStyleUtils`) plus `calc/mergeToken/statistic/statisticToken` from external `@ant-design/cssinjs-utils`.

### Decisive source
```ts
const tableToken = mergeToken<TableToken>(token, {
  tableFontSize: cellFontSize,
  tableBg: colorBgContainer,
  tableRadius: headerBorderRadius,
  ...
  zIndexTableFixed,                    // module const = 2
  tableExpandColumnWidth:
    calc(checkboxSize).add(calc(token.padding).mul(2)).equal(),
  tableFilterDropdownWidth: 120,       // pure constants folded here
  tableFilterDropdownHeight: 264,
  tableScrollThumbSize: 8,             // "Mac scroll bar size"
  tableScrollBg: colorSplit,
});
return [genTableStyle(tableToken), genPaginationStyle(tableToken),
        /* ...15 more feature generators... */];
```

**Flow:** factory merges seed→map→alias→component defaults into `FullToken<'Table'>` → style callback renames component tokens into a `table*`-prefixed second alias layer (`TableToken extends FullToken<'Table'>`) → every feature generator receives that ONE merged token object → array of CSSObjects registered under the component cls.
**Invariant:** feature generators NEVER read raw ComponentToken names — they read only `table*` fields; constants and computed values (`zIndexTableFixed`, dropdown dims, thumb size) are folded at this single site. Runtime consumption is `[hashId, cssVarCls] = useStyle(prefixCls, rootCls)` with `rootCls = useCSSVarCls(prefixCls)` for CSS-var mode. Two real quirks: `resetFont: false` because `genTableStyle` applies `resetComponent(token)` manually inside its own scope; and `genSummaryStyle` appears TWICE in the aggregation array (lines 588 and 594 — idempotent but surprising). `unitless: {expandIconScale: true}` extends the shared global unitless map per-component.

**Probe:** `components/table/__tests__/Table.test.tsx:450-458` ('support wireframe') renders under `ConfigProvider theme={{token:{wireframe:true}}}` snapshot-pinned; `InternalTable.tsx:336-342` shows the same hook instance also feeding JS-side layout defaults.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "genTableStyle mergeToken genStyleHooks tableFontSize", limit: 10 });
```

## Verdict
Adopt the mergeToken renaming layer (one canonical place where public token names become internal style vocabulary) and per-registration unitless/reset options. Adapt the cssinjs-utils `calc()` chain to your arithmetic helper; keep constants folded at registration, not scattered through feature files. Omit the duplicate-generator quirk (fix it instead). Coverage: index.ts + internal.ts + genStyleUtils.ts read in full; all `no_recorded_issue`.
