<!-- capsule-v2 -->
# Dependency Tree Walk — how does one `add` resolve an entire transitive registry-dependency tree into one installable bundle?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** When item A depends on B which depends on C — mixing namespaces, URLs, and bare names — what fetch order and merge policy produce a complete, ordered install payload?

## Two-phase resolution: direct fetch + deferred index pass
**Path/Symbol:** `packages/shadcn/src/registry/resolver.ts:148-398` (`resolveRegistryTree`), `:400-539` (`resolveDependenciesRecursively`), `:81-133` (`fetchRegistryItems`), `:46-77` (`resolveRegistryItemsFromRegistries`).
**Signature:** `resolveRegistryTree(names: string[], config: Config, options?: { requireUniversal?: boolean; useCache?: boolean; sourceCache?: Map<string, Promise<string>> }) => ResolvedItemsTree | null`.
**Data Shape:** Items carry `_source` (the original requested name/URL) added via passthrough schema. Output tree = `{ dependencies, devDependencies, files (target-deduped), tailwind, cssVars, css, docs, envVars?, fonts? }` after deepmerge folds.

### Decisive source
```ts
// Fail LOUD when a dependency needs a namespace the user never configured:
if (!config?.registries) {
  const namespacedDeps = item.registryDependencies.filter(dep => dep.startsWith("@"))
  if (namespacedDeps.length > 0) {
    const { registry } = parseRegistryAndItemFromString(namespacedDeps[0])
    throw new RegistryNotConfiguredError(registry)
  }
} else {
  resolvedDependencies = resolveRegistryItemsFromRegistries(item.registryDependencies, config)
}

// Deliberate non-dedup policy:
// No deduplication - we want to support multiple items with the same name
// from different sources
```

**Flow:** dedupe requested names → parallel `fetchRegistryItems` (per-item dispatch: github → local → url → `@ns` via registries → default `styles/<style>/<name>.json`) → for each result, register dep headers and recurse with a `visited` Set seeded from top-level names → collect leftover bare-name deps into a SECOND phase that resolves them through the shadcn index (`resolveRegistryDependencies` → `styles/<style>/<n>.json` URL set, deduped) → optional `requireUniversal` gate throws if any item lacks explicit targets → inject base-color theme ONLY when resolving `index` → Kahn sort (own capsule) → theme-first stable sort → deepmerge fold of tailwind/cssVars/css/envVars, docs string-concat, `deduplicateFilesByTarget` (LAST file wins per resolved target path).
**Invariant:** Namespaced dependencies without configured registries must throw immediately (never silently drop or mis-route). The walk tolerates same-named items from different sources by NOT deduping on name; only file TARGETS are deduped, last-writer-wins. Cycle protection is per-recursion (`visited.has(dep) → continue`); the seed set means a top-level name is never re-fetched as its own dependency.
**Probe:** `packages/shadcn/src/registry/resolver.test.ts` (2,589 lines / 54 assertions) pins tree shapes incl. namespace errors and multi-source payloads. Runner absent in checkout — pinned by direct test-file read.
**Coverage:** resolver.ts `no_recorded_issue`; api.ts (`getShadcnRegistryIndex`, `parseRegistryCatalog` reject consumer catalogs using `include`, :158-188) `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "resolveRegistryTree dependencies recursively visited", limit: 10 });
```

## Verdict
Adopt the two-phase shape (direct-scheme fetches now, index-routable names later), fail-loud namespace gating, `_source` provenance tracking, and last-wins target dedupe. Adapt the deepmerge fold to your payload vocabulary. Omit shadcn's theme/baseColor injection and universal-item policy unless porting component installs.
