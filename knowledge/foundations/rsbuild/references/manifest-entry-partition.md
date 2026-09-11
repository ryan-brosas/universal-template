<!-- capsule-v2 -->
# Manifest generation by entry — why do initial files come from entrypoints and async from chunk walk?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must keep initial/async partitioning sources separate and the LICENSE.txt ↔ file association.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/manifest.ts` — `generateManifest` 21–173 (chunkEntries map 33–56, initial-from-entries 67–82, async loop 84–106), `normalizeManifestObjectConfig` 178–199, dup-filename warning 244–266.
**Signature:** `generateManifest(htmlPaths, manifestOptions, environment): InternalOptions['generate']`.
**Data Shape:** ManifestData `{allFiles, entries: Record<entryName, {assets?, html?, initial?:{js,css}, async?:{js,css}}>, integrity}`.

### Decisive source
```ts
// Get the initial chunks from `entries`, since they come from
// `compilation.entrypoints.get(entryName).getFiles()`, which ensures
// the correct chunk order (especially important for CSS chunks where order must be preserved).
if (entries[entryName]) for (const filePath of entries[entryName]) {
  const fileURL = manifestOptions.prefix ? ensureAssetPrefix(filePath, publicPath) : filePath;
  if (isCSSPath(filePath)) initialCSS.push(fileURL); else initialJS.push(fileURL);
}
for (const file of chunkFiles) if (!file.isInitial) { /* asyncCSS/asyncJS from chunk walk */ }
```
```ts
if (file.path.endsWith('.LICENSE.txt')) licenseMap.set(file.path.split('.LICENSE.txt')[0], file.path);
...
const relatedLICENSE = licenseMap.get(file.path);   // each manifest file points at its extracted license asset
```
```ts
writeToFileEmit: isDev && writeToDisk !== true,     // dev: emit into memfs unless explicitly on disk
```

**Flow:** every FileDescriptor with a chunk fans out to ALL its recursive entry names (`recursiveChunkEntryNames` — shared with resource-hints); initial arrays are ordered by entrypoint order (CSS order matters for cascade), async arrays accumulate unordered then dedupe via Set for assets; integrity map collected from descriptor.integrity when present; user `generate` override must return an object or loud throw.
**Invariant:** (1) initial MUST come from the entrypoint file list or CSS load order breaks consumers; (2) async MUST come from the chunk walk because entrypoints don't list dynamic imports; (3) duplicate manifest filenames across environments silently overwrite → post-create warn keyed on a Map cleared after check.
**Probe:** e2e `cases/manifest/basic/index.test.ts:4` (allFiles shape), plus custom-path/generate/filter/async-chunks sibling cases; snapshot coverage via build pipeline.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginManifest generateManifest normalizeManifestObjectConfig recursiveChunkEntryNames", limit: 8 });
```

## Verdict
Adopt dual-source partitioning (entrypoint-ordered initial / chunk-walk async), license reassociation, integrity passthrough, and cross-env filename uniqueness warning. Adapt manifest schema keys to host consumers. Omit rspack-manifest-plugin specifics if rolling your own emitter.
