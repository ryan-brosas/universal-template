<!-- capsule-v2 -->
# Structural memo + stable accessors — how does the kernel keep referential stability across renders with inline props?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** How do you memoize data/accessors that callers pass as fresh literals every render, and how do string keys become cached accessor fns?

## useStructuralMemo(depth 0|1) + source-text accessor inference
**Path/Symbol:** `packages/visx-kernel/src/memo/useStructuralMemo.ts` (:10–18) + `memo/shallowEqual.ts` (:27–65); `accessors/normalizeAccessor.ts` (:39–59); warning bus `warnings.ts:devWarn/setWarnHandler` (:31–76); path builder `path/createPath.ts` (:28–132).
**Signature:** `useStructuralMemo<T>(value: T, depth: 0|1 = 1): T`; `normalizeAccessor<D,V>(input: string | fn): Accessor<D,V>`.
**Data Shape:** depth 0 = `Object.is`; depth 1 = shallowEqual with Date-aware (`getTime`) and array-aware element comparison — deliberately NOT deep.

### Decisive source
```ts
// render-phase ref write is intentional: keeps identity stable WITHOUT effect timing
const valueRef = useRef(value);
if (!isEqual(valueRef.current, value, depth)) valueRef.current = value;
return valueRef.current;
```
```ts
// d(datum)=>datum.foo is rewritten to a CACHED key lookup so two inline arrows
// with identical body share one Map-cached accessor
const inferredKey = inferSimplePropertyKey(input);   // regex over Function.toString
return inferredKey ? getStringAccessor(inferredKey) : input;
// symbols throw: '@visx/kernel: symbol accessors are not supported in v1.'
```

**Flow:** `useDomain` wraps BOTH inputs (`useStructuralMemo(data, 1)`, `useStructuralMemo(normalizeAccessor(accessor), 0)`) AND its output (depth 1), so `[min,max]` arrays stay referentially equal across renders unless values change → downstream `useMemo` deps don't thrash. Warnings are dedup'd by code+message+details key and reroutable via `setWarnHandler` (returns restore fn).
**Invariant:** shallow-equal Date handling matters because time domains produce NEW Date objects per extent call — plain Object.is would invalidate every render; deep equality would be O(n) on big data. The render-phase mutation (no useEffect) is what makes the value usable in the SAME render's useMemo deps.
**Probe:** `packages/visx-kernel/test/useStructuralMemo.test.tsx`, `test/normalizeAccessor.test.ts`, `test/warnings.test.ts`, `test/path.test.ts`, `test/useDomain.test.tsx`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useStructuralMemo shallowEqual", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "normalizeAccessor simpleArrowPattern", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all four kernel utilities verbatim (framework-portable); adapt warn codes to your domain; omit the v1 API-surface audit tests.
