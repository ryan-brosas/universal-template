<!-- capsule-v2 -->
# Solid splitProps — how do group proxies claim keys exactly once and keep the rest view consistent?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What happens when the same key appears in multiple groups, on both proxy (store) and plain-object paths?

## splitProps: claimed-set + blocked-rest proxy
**Path/Symbol:** `packages/solid/src/render/component.ts:splitProps` (:288-357).
**Signature:** `splitProps<T, K extends [readonly (keyof T)[], ...(readonly (keyof T)[])[]]>(props: T, ...keys: K): SplitProps<T, K>` — returns N group objects + 1 rest object.
**Data Shape:** proxy path when `$PROXY in props`; each group gets `{owned: PropertyKey[]}`; rest proxy gets `blocked = len > 1 ? keys.flat() : keys[0]`.

### Decisive source
```ts
const claimed = new Set<PropertyKey>();
const res = keys.map(k => {
      // a key belongs to the first group that lists it (matches non-proxy path)
      const owned = k.filter(property => !claimed.has(property) && (claimed.add(property), true));
      return new Proxy(
        {
          get(property) { return owned.includes(property) ? props[property as any] : undefined; },
          has(property) { return owned.includes(property) && property in props; },
          keys() { return owned.filter(property => property in props); }
        },
        propTraps
      );
});
res.push(new Proxy({
      get(property) { return blocked.includes(property) ? undefined : props[property as any]; },
      has(property) { return blocked.includes(property) ? false : property in props; },
      keys() { return Object.keys(props).filter(k => !blocked.includes(k)); }
}, propTraps));
```

**Flow:** each key goes to the FIRST group listing it (`claimed` set); later groups listing it see nothing. The rest object INVERTS the union of all groups — get/has/keys all exclude blocked keys, so `{...rest}` never leaks claimed props. Reads delegate to the ORIGINAL props (getters stay live through the pass-through).
**Invariant:** Group membership is by first-listing, not value — pinned by "SplitProps with keys shared across groups assigns to first group only" (component.spec :420-445) which asserts identical behavior for plain objects AND stores. Descriptor preservation differs per path: plain path copies property descriptors verbatim ("clones the descriptor" test :349-381: getters keep identity, non-configurable stays), while the proxy path preserves liveness but presents manufactured descriptors. `__proto__` JSON-bomb safety is pinned (:447-455): pollution cannot escape either direction.
**Probe:** `grep -c 'const claimed = new Set<PropertyKey>();' packages/solid/src/render/component.ts` → `1`. Behavior pinned by describe("SplitProps Props") :325-470.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "splitProps owned blocked claimed", limit: 10 });
```

## Verdict
Adopt first-group-wins + inverted-rest semantics for any destructuring-with-defaults layer. Adapt descriptor handling to host needs. Omit the plain-object branch if targets are always proxied.
