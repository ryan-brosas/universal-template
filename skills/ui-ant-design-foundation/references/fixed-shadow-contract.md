<!-- capsule-v2 -->
# Fixed-column shadow contract — how do sticky-cell and container edge shadows layer, toggle, and stack?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter implementing fixed/sticky columns needs the two-plane shadow machinery, its z-index algebra, and which parts are deliberately NOT tokens.

## Shadow primitive and planes
**Path/Symbol:** `components/table/style/fixed.ts:getShadowStyle` (6–16), `genFixedStyle` (18–93).
**Signature:** `getShadowStyle({colorSplit}: Pick<TableToken,'colorSplit'>): [left: CSSObject, right: CSSObject]`.
**Data Shape:** two consumers of the tuple — `genFixedStyle` (LTR) and `rtl.ts` (mirrored); shadow color input is exactly one token (`colorSplit`).

### Decisive source
```ts
const leftShadowStyle = { boxShadow: `inset 10px 0 8px -8px ${shadowColor}` };
const sharedShadowStyle = {           // pseudo-element geometry
  position: 'absolute', top: 0,
  bottom: calc(lineWidth).mul(-1).equal(),
  width: 30, transition: `box-shadow ${motionDurationSlow}`,
  content: '""', pointerEvents: 'none',
};
[fixCellCls]: {
  zIndex: `calc(var(--z-offset-reverse) + ${zIndexTableFixed})`,
  '&-start-shadow-show:after': leftShadowStyle,   // visibility class from rc-table
},
[`${componentCls}-container`]: {
  '&:before, &:after': { ...sharedShadowStyle,
    zIndex: `calc(var(--columns-count) * 2 + ${zIndexTableFixed} + 1)` },
},
[`${componentCls}-has-fix-start ${componentCls}-container:before`]: { display: 'none' },
```

**Flow:** sticky cells draw their own `::after` shadow positioned just past the cell (`insetInlineStart:100%` / `insetInlineEnd:100%`, width 30, bottom `-lineWidth` so it overlaps the row border); the container draws edge `:before/:after` shadows for sides WITHOUT fixed columns (`-has-fix-*` suppresses them); rc-table toggles `-fix-start/end-shadow-show` / `-start/end-shadow-show` classes at scroll edges to fade shadows in/out via `motionDurationSlow`.
**Invariant:** geometry constants (10px/8px/-8px blur-offset, 30px width) are deliberately NOT tokens — source comment: "Follow style is magic of shadow which should not follow token"; only the COLOR is tokenized. z-index is computed in CSS from runtime-provided custom properties: cells use `var(--z-offset-reverse) + 2`, container edges use `var(--columns-count) * 2 + 2 + 1`. Those CSS variables are emitted per-cell by the EXTERNAL `rc-table` package (verified absent from this checkout — no node_modules; snapshots like `__tests__/__snapshots__/empty.test.tsx.snap:402` show the inline `--z-offset/--z-offset-reverse` styles rc-table renders). Porting without rc-table means you own emitting those vars.

**Probe:** snapshot evidence `components/table/__tests__/__snapshots__/empty.test.tsx.snap:402-464` (`--z-offset: 22; --z-offset-reverse: 11` on fixed cells); class-name contract cross-checked against `rtl.ts:37-49`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "getShadowStyle genFixedStyle colorSplit sticky", limit: 10 });
```

## Verdict
Adopt the single-color-input shadow primitive, the cell+container two-plane split with has-fix suppression, and CSS-var-based z-index arithmetic. Adapt the shadow-show class emission to your scroll-position hook (antd delegates it to rc-table). Omit copying the magic geometry numbers blindly — port them as named non-token constants. Coverage: fixed.ts read in full (95 lines), `no_recorded_issue`; external boundary recorded as caveat, not silently assumed.
