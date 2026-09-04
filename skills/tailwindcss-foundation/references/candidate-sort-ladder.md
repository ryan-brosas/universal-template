<!-- capsule-v2 -->
# Candidate sort ladder — how are compiled utilities ordered deterministically regardless of scan order?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** Given candidates arriving in arbitrary order, what total order makes `.p-1` before `.px-1` before `.pl-1`, `truncate` (3 decls) before `.text-clip` (1), and `hover:*` after all unvarianted rules?

## compileCandidates sort phase
**Path/Symbol:** `packages/tailwindcss/src/compile.ts:11-121` (`compileCandidates`; comparator at :83-115), `packages/tailwindcss/src/compile.ts:360-402` (`getPropertySort`), `packages/tailwindcss/src/design-system.ts:190-213` (`getVariantOrder`).
**Signature:** `compileCandidates(rawCandidates, designSystem, { onInvalidCandidate?, respectImportant? }) → { astNodes, nodeSorting }`.
**Data Shape:** per-node sort record `{ properties: { order: number[]; count: number }, variants: bigint, candidate: string }`; `variants` is a bitmask of variant positions from `getVariantOrder()`.

### Decisive source
```ts
let variantOrder = 0n
for (let variant of candidate.variants) {
  variantOrder |= 1n << BigInt(variantOrderMap.get(variant)!)
}
...
astNodes.sort((a, z) => {
  let aSorting = nodeSorting.get(a)!
  let zSorting = nodeSorting.get(z)!
  // Sort by variant order first
  if (aSorting.variants - zSorting.variants !== 0n) {
    return Number(aSorting.variants - zSorting.variants)
  }
  ...offset loop over property order arrays...
  return (
    (aSorting.properties.order[offset] ?? Infinity) -
      (zSorting.properties.order[offset] ?? Infinity) ||
    zSorting.properties.count - aSorting.properties.count ||
    compare(aSorting.candidate, zSorting.candidate)
  )
})
```

**Flow:** parse each raw candidate once (invalid → `onInvalidCandidate` + memo in `designSystem.invalidCandidates`) → compile to AST nodes with a `propertySort` computed by BFS over declarations (`getPropertySort`: index of the property in the global `GLOBAL_PROPERTY_ORDER` table, with a one-shot `--tw-sort` value override for polyfill-style utilities like `space-x-*`) → assign bigint variant mask → single sort.
**Invariant:** Ordering is a pure function of the candidate set, never of iteration order; stacked variants sort as a unit between their members' positions (`hover:focus:flex` lands before `disabled:flex` because every member precedes it). Missing property indexes sort last (`?? Infinity`). The bigint subtraction is exact — do not replace with float math when variant count can exceed 53 bits of spread.
**Probe:** `packages/tailwindcss/src/index.test.ts:1130` (property order, input shuffled with `Math.random()`), :1170 (property-count tiebreak), :1195 (`--tw-sort` override puts `space-x-2` next to `gap-4` not `margin`), :1384 ("sort variants and stacked variants by variant position" — comment states the positional invariant explicitly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "compileCandidates sort variants property order compare", filePattern: "packages/tailwindcss/src/*", limit: 10, fields: ["lines"] });
```
Observed top hits: `Variants.compare … variants.ts 214-281`, `sort.getClassOrder … sort.ts 4-30`, `compile.compileCandidates … compile.ts 11-121`, `compile.getPropertySort … compile.ts 360-402`.

## Verdict
Adopt the four-level ladder (variant bitmask → first differing global property index → declaration count → alphabetical candidate name) and the `--tw-sort` internal override hook. Adapt the concrete `GLOBAL_PROPERTY_ORDER` table to your utility set. Omit Tailwind's specific property ordering values unless replicating its CSS output byte-for-byte.
