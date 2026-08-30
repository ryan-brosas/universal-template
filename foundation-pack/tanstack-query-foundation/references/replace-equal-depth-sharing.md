<!-- capsule-v2 -->
# replaceEqualDeep structural sharing — how does referential identity survive refetches?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How do you deep-compare two JSON trees and return the ORIGINAL object when nothing changed, replacing only genuinely-changed subtrees?

## copy-on-write diff with identity fast path
**Path/Symbol:** `packages/query-core/src/utils.ts:replaceEqualDeep` (lines 287–334).
**Signature:** `replaceEqualDeep<T>(a: unknown, b: T, depth?: number): T`.
**Data Shape:** plain arrays / plain objects / anything else (returned as-is when not both-plain).

### Decisive source
```ts
if (a === b) return a
if (depth > 500) return b
const array = isPlainArray(a) && isPlainArray(b)
if (!array && !(isPlainObject(a) && isPlainObject(b))) return b
const aItems = array ? a : Object.keys(a)
const aSize = aItems.length
const bItems = array ? b : Object.keys(b)
const bSize = bItems.length
const copy: any = array ? new Array(bSize) : {}
let equalItems = 0
for (let i = 0; i < bSize; i++) {
  const key: any = array ? i : bItems[i]
  const aItem = a[key]
  const bItem = b[key]
  if (aItem === bItem) {
    copy[key] = aItem
    if (array ? i < aSize : hasOwn.call(a, key)) equalItems++
    continue
  }
  if (aItem === null || bItem === null ||
      typeof aItem !== 'object' || typeof bItem !== 'object') {
    copy[key] = bItem
    continue
  }
  const v = replaceEqualDeep(aItem, bItem, depth + 1)
  copy[key] = v
  if (v === aItem) equalItems++        // recursion KEPT the child → counts as equal
}
return aSize === bSize && equalItems === aSize ? a : copy
```

**Flow:** reference equality → keep `a`. Non-plain pairs (Dates, class instances, functions) → take `b` wholesale. Otherwise build `copy`, recursing into children; each child that comes back referentially identical to `a`'s child increments equalItems. If sizes match and EVERY item counted equal → return `a` itself (zero allocation escapes), else return `copy` where unchanged children still alias old references.
**Invariant:** (1) the equalItems counter is fed by RECURSION RESULTS (`v === aItem`), which is what makes identity propagate up from arbitrarily deep unchanged subtrees — a naive shallow-count version breaks memoization one level down; (2) depth cap 500 returns `b` (correctness preserved, stack safety); (3) objects compare by b-keys with hasOwn check on a — added/removed keys break equality via size/count arithmetic; (4) isPlainArray requires `length === Object.keys(value).length` (no sparse/holey arrays masquerading).
**Probe:** self-contained live probe from repo root: `node --experimental-strip-types -e "const{registerHooks}=require('node:module');registerHooks({resolve(s,c,next){if(s.startsWith('.')&&!/\.[a-z]+$/.test(s))s+='.ts';return next(s,c)}});import('./packages/query-core/src/utils.ts').then(m=>{const a={x:{y:1}};console.log('SHARED:',m.replaceEqualDeep(a,{x:a.x})===a)})"` → prints `SHARED: true`. Executed GREEN this pass.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^isPlainArray$", limit: 3 });
```

## Verdict
Adopt wholesale as the universal memo-friendly merge for JSON-shaped data. Adapt the depth cap for hostile inputs. Omit isPlainObject strictness only if your producer guarantees plain JSON. Direct tests: `__tests__/utils.test.tsx` replaceEqualDeep matrix incl. deeply-nested cases.
