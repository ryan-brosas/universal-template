<!-- capsule-v2 -->
# Topological Source-Hash Sort — how are resolved items ordered so dependencies install first, even with same-named items from different sources?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** When the resolved payload may contain two different items both named `button` (from `@acme` and a URL), what node identity makes Kahn's algorithm still order every dependency before its dependent?

## name::source-hash node identity + cycle-tolerant Kahn's
**Path/Symbol:** `packages/shadcn/src/registry/resolver.ts:697-818` (`topologicalSortRegistryItems`), `:644-656` (`computeItemHash`), `:658-695` (`extractItemIdentifierFromDependency`).
**Signature:** `computeItemHash(item: {name}, source?: string) => `${name}::${sha256(source||name).slice(0,8)}``; `topologicalSortRegistryItems(items, sourceMap: Map<item, string>) => items[]`.
**Data Shape:** Four parallel maps keyed by hash: itemMap, inDegree, adjacencyList, plus `depToHashes: Map<depString, hash[]>` populated under BOTH the item's `name` and its `_source`, so a dependency string written either way resolves to candidate nodes.

### Decisive source
```ts
const identifier = source || item.name
const hash = createHash("sha256").update(identifier).digest("hex").substring(0, 8)
return `${item.name}::${hash}`

// edge building — disambiguate dep string -> node:
const exactMatches = depToHashes.get(dep) || []
if (exactMatches.length === 1)        depHash = exactMatches[0]
else if (exactMatches.length > 1)     depHash = exactMatches[0]   // first wins
else {
  const { name } = extractItemIdentifierFromDependency(dep)
  const nameMatches = depToHashes.get(name) || []
  if (nameMatches.length > 0)         depHash = nameMatches[0]
}

// cycle tolerance:
if (sorted.length !== items.length) {
  // Items not in sorted are part of circular dependencies
  const sortedHashes = new Set(sorted.map(...computeItemHash...))
  items.forEach(item => { if (!sortedHashes.has(hash)) sorted.push(item) })
}
```

**Flow:** assign each item a hash from `_source || name` (distinct sources → distinct nodes even for identical names) → build `depToHashes` under both name and source keys → for each item's `registryDependencies`, find the dep's node (exact dep string, else extract bare name/URL-basename/local-basename via `extractItemIdentifierFromDependency`) and add edge dep→dependent with in-degree bump → seed queue with zero in-degree → Kahn BFS → if any nodes remain (cycle), append them unsorted rather than dropping.
**Invariant:** Sorting must never LOSE items: cycles degrade to "unsorted tail", never an error or omission. Node identity must include source, otherwise two same-named items collapse and one silently disappears from the payload. Ambiguous multi-match deps deterministically pick the first candidate.
**Probe:** No dedicated unit test file for `topologicalSortRegistryItems` at this pin — behavior is exercised through `resolver.test.ts` tree-order assertions (2,589 lines). Recorded caveat: ordering contract pinned by resolver tests' output shapes, not by an isolated sort suite; runner absent in checkout regardless.
**Coverage:** resolver.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "topologicalSortRegistryItems inDegree adjacency queue", limit: 10 });
```

## Verdict
Adopt source-hashed node identity + dual-key (name and source) dependency lookup + append-don't-drop cycle handling for any install-order problem over possibly-conflicting payloads. Adapt hash width/algorithm to your collision needs. Omit the theme-first post-sort unless you have registry:theme-type items.
