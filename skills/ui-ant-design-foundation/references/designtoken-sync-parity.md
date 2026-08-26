<!-- capsule-v2 -->
# Sync token parity — how do you compute design tokens outside React and stay output-equal to the hook?

**Source:** Ant Design MIT `master@977d8e037a4841bb847b8a40ffd1f79b23264826`; Codebase Memory `ui-ant-design`. **Question:** A porter needs a React-free token computation that will not drift from the context-driven path.

## `getDesignToken` — the sync twin
**Path/Symbol:** `components/theme/getDesignToken.ts:getDesignToken` (lines 9–16).
**Signature:** `getDesignToken(config?: ThemeConfig): AliasToken`.
**Data Shape:** `ThemeConfig = { token?, algorithm?, components?, ... }` from `components/config-provider/context`; returns a fully formatted AliasToken.

### Decisive source
```ts
const getDesignToken = (config?: ThemeConfig): AliasToken => {
  const theme = config?.algorithm ? createTheme(config.algorithm) : defaultTheme;
  const mergedToken = {
    ...seedToken,
    ...config?.token,
  };
  return getComputedToken(mergedToken as any, { override: config?.token }, theme, formatToken);
};
```

**Flow:** user config's `algorithm` (single or array) is folded into one cssinjs `Theme` via `createTheme`, else the singleton `defaultTheme` (`themes/default/theme.ts`: `createTheme(defaultDerivative)`) → seed merged with `config.token` → cssinjs's **own** `getComputedToken(mergedSeed, {override: config?.token}, theme, formatToken)` runs with the formatter **injected as an argument**.

**Invariant:** The sync result must deep-equal what `useToken()` produces for the same config. This is pinned directly — `__tests__/token.test.tsx:259-294` asserts `expect(token).toEqual(hookToken)` for default, custom-token (`colorPrimary '#189cff'` → `token.colorPrimary === '#189cff'`), and custom-algorithm (`[darkAlgorithm, compactAlgorithm]` → `colorPrimary '#1668dc'`) configs. Two consequences a porter must keep:
1. User `token` entries are applied twice by design — once into the seed (so derivation sees them) and once as `override` (so alias-stage wins). Dropping either half breaks parity.
2. The hook path hard-codes `formatToken` inside its local `getComputedToken` (useToken.ts:81); the sync path receives it as a parameter. If you fork one, diff both call sites.

**Probe:** `components/theme/__tests__/token.test.tsx:259-294` (`describe('getDesignToken')`) — three-way parity default/custom/algorithm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-ant-design", query: "getDesignToken createTheme formatToken", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "one formatter function, two entry points, equality-tested" as the portable architecture; adopt the double-application of user tokens (seed + override) as behavior. Adapt `createTheme`/cssinjs cache internals to your host. Omit antd's ThemeConfig surface beyond what your port supports. Coverage caveat: none — getDesignToken.ts checked `no_recorded_issue`; upstream jest runner unavailable in this clean checkout, so probe evidence is the direct test source at pin.
