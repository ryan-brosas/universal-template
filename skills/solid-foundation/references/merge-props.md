<!-- capsule-v2 -->
# Solid mergeProps — how do props proxies keep getters live, prefer last-defined, and skip undefined?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What is the exact precedence and reactivity contract of merged props?

## component.ts: propTraps + dual proxy/plain paths
**Path/Symbol:** `packages/solid/src/render/component.ts:mergeProps` (:199-277) with `propTraps` (:120-149), `resolveSource`, `resolveSources`.
**Signature:** `mergeProps<T extends unknown[]>(...sources: T): MergeProps<T>` — variadic; later sources win.
**Data Shape:** source entries may be plain objects, getters, or FUNCTIONS (auto-wrapped in `createMemo(s)` at :206-208 — the JSX spread-props pattern); `proxy` flag set if any source is a store proxy (`$PROXY in s`) or function.

### Decisive source
```ts
get(property: string | number | symbol) {
      for (let i = sources.length - 1; i >= 0; i--) {
        const v = resolveSource(sources[i])[property];
        if (v !== undefined) return v;
      }
},
has(property) {
      for (let i = sources.length - 1; i >= 0; i--) {
        if (property in resolveSource(sources[i])) return true;
      }
      return false;
},
keys() {
      const keys = [];
      for (let i = 0; i < sources.length; i++)
        keys.push(...Object.keys(resolveSource(sources[i])));
      return [...new Set(keys)];
}
```

**Flow (proxy path):** every read walks sources LAST→FIRST returning the first non-undefined value — so later defaults lose to earlier real values but win over undefined holes. Getters stay live because reads re-enter the original getter each access; `getOwnPropertyDescriptor` manufactures a fresh `{configurable, enumerable, get}` descriptor so spread/`Object.keys` work. Writes/deletes are swallowed (`trueFn`) — merged props are read-only.
**Invariant:** `undefined` means "not provided" — a source explicitly setting `value: undefined` does NOT shadow a later/earlier defined value ("skips undefined values", component.spec :67-85), yet `"a" in mergeProps({a: undefined})` stays TRUE ("includes undefined property", :86-97): presence and value are orthogonal. The non-proxy fallback path (:234-277) rebuilds a static target with combined getter chains via `resolveSources.bind(...)` and SKIPS `__proto__`/`constructor` keys entirely (:245).
**Probe:** `grep -c 'key === "__proto__" || key === "constructor" continue' packages/solid/src/render/component.ts` → matches the guarded loop line `if (key === "__proto__" || key === "constructor") continue;`. Behavior pinned by component.spec describe("mergeProps") :53-231 (20 tests incl. "is safe", "sets already prototyped properties").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "mergeProps propTraps resolveSources", limit: 10 });
```

## Verdict
Adopt last-wins-skip-undefined + live-getter semantics for any props/default layering. Adapt function-source memoization to host. Omit the plain-object path only when Proxy support is guaranteed.
