<!-- capsule-v2 -->
# CSS-var naming contract — how are `--ant-<component>-*` variables named, unitless-classed, and wired into style hooks?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter building a cssinjs-style style-hook factory must reproduce variable naming, fallbacks, and the unitless/ignore/preserve classes exactly.

## `genCssVar` naming pair
**Path/Symbol:** `components/theme/util/genStyleUtils.ts:genCssVar` (lines 48–60); factory call at lines 10–43.
**Signature:** `genCssVar(antCls: string, component: string): readonly [varName: (name)=>`--${string}`, varRef: (name, fallback?)=>`var(--${string})`]`.
**Data Shape:** 65 inbound consumers; internal helpers `varName` (51 users) and `varRef` (42 users).

### Decisive source
```ts
const cssPrefix = `--${antCls.replace(/\./g, '')}-${component}-` satisfies `--${string}`;
const varName: CssVarName = (name) => `${cssPrefix}${name}`;
const varRef: CssVarRef = (name, fallback) =>
  fallback ? `var(${cssPrefix}${name}, ${fallback})` : `var(${cssPrefix}${name})`;
```

**Flow:** class-scoped selector prefix (`ant`) is stripped of dots to yield a valid custom-property namespace → per-component suffix → `varName` for declarations, `varRef` (optional fallback) for consumption.
**Invariant:** An EMPTY configured prefix must still produce a syntactically valid var that does NOT silently fall back to `--ant-…`. Test pins both directions (`token.test.tsx:370-391`): default `cssVar.colorLink === 'var(--ant-color-link)'`; with `{prefix:'', key:''}` the ref starts with `'var(--'`, contains `'color-link'`, and does NOT start with `'var(--ant-'`.

## Style-hook factory wiring
```ts
export const { genStyleHooks, genComponentStyleHook, genSubStyleComponent } = genStyleUtils<
  ComponentTokenMap, AliasToken, SeedToken
>({
  usePrefix: () => { const { getPrefixCls, iconPrefixCls } = useContext(ConfigContext);
    return { rootPrefixCls: getPrefixCls(), iconPrefixCls }; },
  useToken: () => { const [theme, realToken, hashId, token, cssVar, zeroRuntime] = useLocalToken();
    return { theme, realToken, hashId, token, cssVar, zeroRuntime }; },
  useCSP: () => { const { csp } = useContext(ConfigContext); return csp ?? {}; },
  getResetStyles: (token, config) => [
    linkStyle, { '&': linkStyle },
    genIconStyle(config?.prefix.iconPrefixCls ?? defaultIconPrefixCls),
  ],
  getCommonStyle: genCommonStyle,
  getCompUnitless: (() => unitless) as GetCompUnitless<...>,
});
```
- ONE shared `unitless` map (exported from `useToken.ts`: lineHeight*, opacityLoading, fontWeightStrong, zIndexPopupBase/Base, opacityImage) feeds BOTH token computation and the css-var emitter — keep it single-sourced.
- `ignore` (motionBase/motionUnit) keeps tokens out of emitted vars entirely; `preserve` (screen* family) keeps them as vars even though they're static.
- Reset styles inject as a triple `[linkStyle, {'&': linkStyle}, iconStyle]` — the `'&'` self-reference matters for nested selectors.
- The component-token test proves the whole chain end-to-end: `Input` style lands as `--ant-input-hover-border-color:#4096ff` on the input element itself (`token.test.tsx:354`).

**Probe:** `components/theme/__tests__/token.test.tsx:363-391` (var refs + empty-prefix), `341-361` (component-scoped var values under per-component algorithms).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "genCssVar varName varRef unitless preserve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dot-stripped prefix construction, the name/ref pair with optional fallback, and single-source unitless classes. Adapt ConfigContext-derived defaults (root prefix cls from `getPrefixCls()`, key `'css-var-root'`) to your host's config surface. Omit antd's specific `--ant-` namespace if rebranding — but keep the empty-prefix non-fallback semantics. Coverage: genStyleUtils.ts read in full (60 lines), `no_recorded_issue`; consumer count taken from graph degree columns.
