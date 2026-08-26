<!-- capsule-v2 -->
# File size report — how are cross-build size diffs computed from hash-stripped snapshot files?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know why asset names are hash-stripped with a lowercase-hex-8+ regex, when gzip is computed, and how the diff snapshot file is keyed and persisted.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/fileSize.ts:normalizeFilePath` (69–72), `excludeAsset` (100–104), `isSignificantDiff`/`formatDiff` (107–118), `getFilePath` (178–183), `printFileSizes` (202–499), `pluginFileSize.setup` (522–588).
**Signature:** `normalizeFilePath(filePath: string): string`; `pluginFileSize(context): RsbuildPlugin` tapping `onAfterBuild`.
**Data Shape:** `SizeSnapshots = Record<envName, {files: Record<normalizedPath,{size,gzippedSize?}>, totalSize, totalGzipSize}>` persisted at `<cachePath>/rsbuild/file-sizes[-<hash(configFile)>].json`.

### Decisive source
```ts
// strip content hashes for cross-build comparison: 8+ LOWERCASE hex between dots
return filePath.replace(/\.[a-f0-9]{8,}\./g, '.');
// uppercase hex deliberately NOT stripped — pinned by test 'should handle uppercase hex digits'
```
```ts
// query strings split BEFORE exclusion/matching; asset Source access deferred until needed
const filePath = assetName.slice(0, assetName.indexOf('?'));   // -1 → whole name
if (!exclude && EXCLUDE_ASSET_REGEX.test(filePath)) continue;  // /\.(map|LICENSE\.txt|d\.(ts|mts|cts))$/
// Accessing an asset retrieves its Source through the Rust-JS bridge, so filter by filename before reading it.
const content = options.compressed && isCompressible(filePath) ? value.source() : undefined;
const size = content === undefined ? value.size() : Buffer.byteLength(content);
```
```ts
// diff gating + snapshot keying in setup()
const showDiff = environments.some(e => typeof e.config.performance.printFileSize === 'object' && e.printFileSize.diff);
const snapshotHash = showDiff && configFile ? await hash(configFile) : '';
const snapshotPath = showDiff ? getSnapshotPath(api.context.cachePath, snapshotHash) : '';
// per-asset inline diff appended only when |diff| >= 10 bytes (isSignificantDiff)
```

**Flow:** on first successful compile (`isFirstCompile`, no build errors), each environment with `printFileSize !== false` is formatted: assets sorted ascending by size, gzip computed only for non-node default targets over compressible extensions (COMPRESSIBLE_REGEX), column widths padded from longest labels, totals with optional custom `total()` formatter. When diff enabled, previous snapshot loaded from disk (missing → no diffs shown), current sizes recorded into a fresh snapshot keyed by normalized path, saved after printing; failures to save are debug-only. Snapshot filename includes hash(configFile) so parallel Rsbuild config files don't collide.

**Invariant:** normalized-path comparison must tolerate changing hashes but not merge distinct chunks sharing a basename path prefix; printFileSizes must never throw the build — wrapped with warn-only catch.

**Probe:** `tests/fileSize.test.ts:4-15` pins excludeAsset matrix (maps/LICENSE/d.ts excluded, js/css/png kept); `:17-73` pins normalizeFilePath edges: adjacent-hash partial strip documented as acceptable, non-hex preserved, <8 length preserved, path separators handled.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginFileSize normalizeFilePath printFileSizes getSnapshotPath excludeAsset", limit: 10 });
```

## Verdict
Adopt hash-stripped snapshot diffs, threshold-gated inline deltas, lazy Rust-bridge source reads, and config-file-keyed snapshots. Adapt thresholds/colors to host UX. Omit CRA-derived formatting minutiae. Coverage caveat: unit tests cover helpers only; pipeline flow verified from source.
