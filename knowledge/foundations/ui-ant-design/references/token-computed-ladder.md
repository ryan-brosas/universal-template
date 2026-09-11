<!-- capsule-v2 -->
# Token computation ladder — how are runtime tokens computed, cached, and how do per-component themes recurse?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter must reproduce antd's runtime token computation without missing the cache-salt contract or the component-level algorithm recursion.

## Runtime hook path (`useToken` → `useCacheToken`)
**Path/Symbol:** `components/theme/useToken.ts:useToken` (lines 107–153), `getComputedToken` (63–104).
**Signature:** `useToken(): [theme, realToken, hashId, realToken2, cssVar, zeroRuntime]` — actually `[Theme<SeedToken,AliasToken>, GlobalToken(real), string(hashId|''), GlobalToken(base), {prefix,key}, boolean]`.
**Data Shape:** Reads `DesignTokenContext` = `{token: seed-level rootDesignToken, hashed, theme, override, cssVar, zeroRuntime}` and `ConfigContext` for `csp`/`getPrefixCls`.

### Decisive source
```ts
const cssVar = {
  prefix: ctxCssVar?.prefix ?? getPrefixCls(),
  key: ctxCssVar?.key ?? 'css-var-root',
};
const salt = `${version}-${hashed || ''}`;
const mergedTheme = theme || defaultTheme;
const [token, hashId, realToken] = useCacheToken<GlobalToken, SeedToken>(
  mergedTheme,
  [defaultSeedToken, rootDesignToken],
  {
    salt,
    override,
    getComputedToken,
    cssVar: { ...cssVar, unitless, ignore, preserve },
    nonce: csp?.nonce,
  },
);
return [mergedTheme, realToken, hashed ? hashId : '', token, cssVar, !!zeroRuntime];
```

**Flow:** context read → cssVar defaults derived client-side → salt pins cache to `(version, hashed)` so upgrades invalidate every cached style → `useCacheToken` computes via injected `getComputedToken(seedTokens, override, theme)` → returns tuple with realToken (override-applied) at index 1 and base token at index 3; empty-string `hashId` when hashing disabled.
**Invariant:** The three token classes exported alongside (`unitless`: lineHeight*/opacityLoading/fontWeightStrong/zIndexPopupBase/zIndexBase/opacityImage; `ignore`: motionBase/motionUnit; `preserve`: whole screen* breakpoint family) must travel with the cache entry or CSS-var emission breaks.

### Component-token recursion
```ts
Object.entries(components).forEach(([key, value]) => {
  const { theme: componentTheme, ...componentTokens } = value;
  let mergedComponentToken = componentTokens;
  if (componentTheme) {
    mergedComponentToken = getComputedToken(
      { ...mergedDerivativeToken, ...componentTokens },
      { override: componentTokens },
      componentTheme,
    );
  }
  mergedDerivativeToken[key] = mergedComponentToken;
});
```
With a per-component `theme`, the FULL pipeline (derivative + format) re-runs seeded with `{...mergedDerivativeToken, ...componentTokens}`; without one, raw `componentTokens` land under the component key unformatted. Test `__tests__/token.test.tsx:341-361` pins this end-to-end: `Input` with `colorPrimary:'#00B96B'` renders `--ant-input-hover-border-color:#4096ff`, flipping to `#20c77c`/`#1fb572` when `algorithm` / `darkAlgorithm` is attached to the *component* config.

**Probe:** `components/theme/__tests__/token.test.tsx` — lines 14–31 (`getHookToken` strips `_hashId/_tokenKey/_themeKey` before comparing), 33–44 (default `colorPrimary:'#1677ff'`, `'blue-6':'#1677ff'`), 341–361, 363–391.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "useToken getComputedToken useCacheToken", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order (seed array → derivative → format → component recursion) and the version-hashed salt as portable behavior. Adapt `useCacheToken`/React-context plumbing to your host's memoization; keep unitless/ignore/preserve maps co-located with computation. Omit antd's specific default values unless porting antd itself. Caveat: hooks resolve via USAGE edges (68 in-degree, 0 CALLS callers) — confirm consumers with search_graph degree columns; all cited paths checked `no_recorded_issue` at generation 2026-08-25T19:59:19Z.
