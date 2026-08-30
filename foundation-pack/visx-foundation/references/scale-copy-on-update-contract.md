<!-- capsule-v2 -->
# Copy-on-update scale contract — why must updateScale call scale.copy() and how do React hooks keep scales stable?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** Applying a config to a d3 scale mutates it — how does visx avoid corrupting the caller's scale, and when do memoized scales rebuild?

## updateScale copies; useScale memos on config identity
**Path/Symbol:** `packages/visx-scale/src/updateScale.ts:updateScale` (:152–161); `packages/visx-scale/src/react/useScale.ts:useScale` (:93–95); `packages/visx-scale/src/createScale.ts:createScale` (:129–174).
**Signature:** `updateScale(scale, config?) => scale` (fresh copy); `useScale(config?) => PickD3Scale`.
**Data Shape:** `updateScale` pre-binds ALL operators (`scaleOperator(...ALL_OPERATORS)` at :8) so any config key works on any passed scale; `createScale` switches on `config.type` with 14 cases and FALLS THROUGH to linear when `type` is absent or unknown.

### Decisive source
```ts
// updateScale implementation — copy BEFORE mutating
function updateScale(scale, config?) {
  return applyAllOperators(scale.copy(), config);
}
```
```ts
// useScale implementation — identity-keyed memo
function useScale(config?: unknown): unknown {
  return useMemo(() => createScale(config as ScaleConfig), [config]);
}
```

**Flow:** `createScale(config)` = dispatch by `type` → per-type factory → `updateLinearScale(scaleLinear(), config)` (each factory pre-selects only the ops its scale supports). `updateScale(scale, config)` = copy then apply everything. Hook callers get a NEW scale object only when the config OBJECT IDENTITY changes.
**Invariant:** (1) never mutate a caller-owned scale — `copy()` first, always; the direct test pins reference inequality. (2) Because `useScale` keys on identity, an inline `{domain:[0,10]}` literal in JSX rebuilds the scale every render — hoist configs or accept the churn; downstream consumers must not hold stale references across rebuilds.
**Probe:** `packages/visx-scale/test/updateScale.test.ts :21-25` ("should return a new copy of the scale": `expect(scale).not.toBe(nextScale)`); `test/useScale.test.tsx`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "updateScale applyAllOperators", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-scale/src/updateScale.ts :152-161
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useScale createScale useMemo", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-scale/src/react/useScale.ts :93-95
```

## Verdict
Adopt both contracts (copy-on-update; identity-memo hook) as-is; adapt the overload ladder to your type system or drop it; omit vendor indirection. All cited files clean per coverage check.
