<!-- capsule-v2 -->
# Bounded-Concurrency Validation Sweep — how do you validate every item of a remote catalog without unbounded parallel fetches, while still attributing each failure to its registry file?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** A registry source exposes a catalog whose items may be split across include-files; validating "every item loads" naively means N×M parallel fetches and errors that lost their provenance — what structure fixes both?

## worker-pool over shared cursor + tracking reader decorator + context-derived diagnostics
**Path/Symbol:** `packages/shadcn/src/registry/github.ts:validateGitHubRegistrySource` (:81-157), `mapWithConcurrency` (:437-455), `createGitHubValidationDiagnostic` (:461-507); reader interface `source.ts:RegistrySourceReader` (:32-34).
**Signature:** `validateGitHubRegistrySource(source, options?): Promise<{ valid, cwd, registryFiles, registryFilePaths, items, diagnostics }>`; `mapWithConcurrency<T,R>(items, concurrency, mapper): Promise<R[]>`.
**Data Shape:** Diagnostics are flat records `{ registryFile, message, suggestion?, itemName?, itemIndex?, filePath?, includePath? }`; the tracking reader is a one-method decorator over `readText`.

### Decisive source
```ts
// decorate the real reader to RECORD which catalog files were traversed:
const trackingReader: RegistrySourceReader = {
  async readText(filePath) {
    if (filePath.endsWith("registry.json")) {
      registryFiles.add(`${sourceLabel}/${filePath}`)   // includes expansion shows up here
    }
    return sourceReader.readText(filePath)
  },
}
const itemDiagnostics = await mapWithConcurrency(
  registry.items, GITHUB_VALIDATION_CONCURRENCY /* = 8 */,
  async (item, itemIndex) => {
    try { await loadRegistryItemFromSource(item.name, trackingReader, {...}); return null }
    catch (error) { return createGitHubValidationDiagnostic(error, {...}) }
  }
)

// order-preserving worker pool over a shared cursor:
let nextIndex = 0
const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
  while (nextIndex < items.length) {
    const itemIndex = nextIndex++
    results[itemIndex] = await mapper(items[itemIndex]!, itemIndex)
  }
})
await Promise.all(workers)
```

**Flow:** load the catalog once through a decorated reader that records every `registry.json` path actually touched (so include-expansion is measured, not assumed) → fan the items through an 8-fiber pool where workers pull indices from one shared cursor and write into a pre-sized results array (output order == input order without per-item await bookkeeping) → per-item failures become flat diagnostics with fields recovered from `RegistryError.context` (`registryFile`, `itemIndex`, `itemFilePath`/`filePath`, `includePath`), each prefixed with the source label; a catalog-level failure short-circuits to ONE diagnostic with `items: 0`.
**Invariant:** Concurrency must be bounded even though every item validation fans out into multiple file reads (test asserts max in-flight ≤ 8 AND > 1, i.e., the bound is real but not serialized). Results must stay positionally aligned with input. Validation must COLLECT failures, not throw on first item error.
**Probe:** `packages/shadcn/src/registry/github.test.ts` — :617-672 include-traversal reports exact registryFilePaths; :674-723 sixteen items, delayed handler, maxActiveRequests ≤8 and >1; :725-762 duplicate-name diagnostic attributed to root registry file; :764-819 missing-file diagnostic carries itemName/itemIndex/filePath/suggestion. Runner caveat: node_modules absent in checkout — pinned by direct reads.
**Coverage:** github.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "validateGitHubRegistrySource mapWithConcurrency tracking reader diagnostics registry files", limit: 8 });
// observed: mapWithConcurrency #1 (:437-455), validateGitHubRegistrySource #2 (:81-157),
// createGitHubRegistrySourceReader #6
```

## Verdict
Adopt the shared-cursor worker pool whenever you need bounded concurrency WITH output-order preservation (simpler than chunked Promise.all and preserves lazy pull semantics), and the readText-decorating tracking reader for any "which resources did this operation touch" audit. Adapt the diagnostic field extraction to your error context vocabulary. Omit the GitHub-specific source-label prefixing if your errors already carry absolute identifiers.
