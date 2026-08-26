<!-- capsule-v2 -->
# Token→layout dual consumption — how do component tokens feed BOTH generated CSS and JS-side layout defaults, and who wins?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter whose component measures layout in JS (column widths, virtual rows) needs the token-default + prop-override merge contract.

## Dual-plane consumption
**Path/Symbol:** `components/table/InternalTable.tsx:336-345` (runtime) with `components/table/style/selection.ts:28-36` (style plane).
**Signature:** `{ columnWidth: token.Table?.selectionColumnWidth, ...customizeRowSelection }` — token default first, user props spread after.
**Data Shape:** `const [, token] = useToken()` (position 2 = realToken with override applied — see token-computed-ladder); component namespace accessed as `token.Table?` with optional chaining so non-table themes degrade gracefully.

### Decisive source
```ts
const [, token] = useToken();
const mergedRowSelection = React.useMemo(() => {
  return isPlainObject(customizeRowSelection)
    ? { columnWidth: token.Table?.selectionColumnWidth, ...customizeRowSelection }
    : customizeRowSelection;
}, [customizeRowSelection, token.Table?.selectionColumnWidth]);

const rootCls = useCSSVarCls(prefixCls);
const [hashId, cssVarCls] = useStyle(prefixCls, rootCls);
```

**Flow:** the SAME ComponentToken (`selectionColumnWidth`) reaches two planes: (1) styles — selection column width algebra in `genSelectionStyle` (adds `fontSizeIcon + padding/4` when the selection carries a dropdown, plus `paddingXS*2` when bordered); (2) runtime — the JS-side default for rc-table's `rowSelection.columnWidth`, needed because actual DOM column sizing happens outside generated CSS.
**Invariant:** spread order makes explicit props ALWAYS win over token defaults; the token only fills absence. Both planes read the same merged token object, so a ConfigProvider theme change moves CSS width and JS layout in lockstep — tests pin the whole chain end-to-end: `theme.components.Table.selectionColumnWidth = 200` renders `.ant-table-selection-col` at `width: 200px`, then `rowSelection={{columnWidth: 50}}` overrides to `50px`.

**Probe:** `components/table/__tests__/Table.virtual.test.tsx:130-174` — both assertions quoted above, executed against real DOM via `toHaveStyle`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "mergedRowSelection selectionColumnWidth useToken InternalTable", limit: 10 });
```

## Verdict
Adopt "token defaults + prop spread wins" for every measured-layout input, keeping style and JS planes on one merged token. Adapt `token.Table?` namespacing to your component-token registry shape. Omit the useMemo dependency subtleties unless your token identity is unstable. Coverage: InternalTable.tsx decisive range read directly; selection.ts whole file; both `no_recorded_issue`.
