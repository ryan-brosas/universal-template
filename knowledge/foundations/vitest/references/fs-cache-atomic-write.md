<!-- capsule-v2 -->
# Atomic cache file format — how is transformed code stored on disk so concurrent workers never read a torn write, and when is the whole cache nuked?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** What does a safe on-disk module-cache entry look like (write protocol + payload framing + invalidation trigger) for a multi-process test runner?

## Write-then-rename + trailing-metadata framing
**Path/Symbol:** `packages/vitest/src/node/cache/fsModuleCache.ts:atomicWriteFile` (:383–399), `saveCachedModule` (:142–160), `readCachedFileConcurrently` (:97–112), `ensureCacheIntegrity` (:317–366), `getLockfileHash` (:485–507).
**Signature:** `async function atomicWriteFile(realFilePath: string, data: string): Promise<void>`; `saveCachedModule(cachedFilePath, fetchResult, importedUrls = [], mappings = false)`.
**Data Shape:** One cache file = `<transformed code>\n//# vitestCache=<base64(flatted meta)>`. Meta carries `{ url, id, file, importedUrls, mappings, moduleType }` (flatted-JSON → base64). A MODULE-LEVEL `parallelFsCacheRead: Map<path, Promise>` dedupes concurrent reads of the same path and deletes its entry in `.finally` — the in-flight promise IS the single-flight gate.

### Decisive source
```ts
const tmpFilePath = join(dir, `.tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`)
try {
  await writeFile(tmpFilePath, data, 'utf-8')
  await rename(tmpFilePath, realFilePath)   // atomic on POSIX
}
finally { /* unlink tmp if it still exists */ }
```
```ts
// ensureCacheIntegrity — lockfile change ⇒ whole-workspace cache reset
if (!metadata)            { /* store new hash, DON'T clear */ }
if (metadata.lockfileHash === currentLockfileHash) return
await this.clearCache(false)
```

**Flow:** write to `.tmp-*` sibling then `rename` (atomic; readers see complete files only) → readers split on the LAST `//# vitestCache=` occurrence; a file WITHOUT the comment marker is treated as uncached (Vite re-transforms) rather than corrupt → lockfile hash (8-hex-char sha256 prefix over lockfile content + patched-dir mtime where the manager tracks patches) is checked once per run against `_metadata.json` living ONLY in the root cache dir so per-project overrides still share one invalidation epoch.
**Invariant:** The metadata file must live at the WORKSPACE root even when projects point elsewhere (projects cross-reference each other's files; lockfile changes are workspace-global). Missing metadata ≠ mismatch: first run stores a hash and does NOT clear. Metadata writes are best-effort (failure logged, never aborts the run). The cache comment must be searched with `lastIndexOf` because transformed code could itself contain the literal. A porter who writes directly to the final path ships torn reads under parallel workers (#7531 exists for exactly this).
**Probe:** `grep -c 'atomicWriteFile' packages/vitest/src/node/cache/fsModuleCache.ts` = 2 (:158 call site :158 + def :383); `grep -c '# vitestCache=' …` = 1 (:17 constant); `grep -c 'lockfileHash === currentLockfileHash' …` = 1 (:352 equality gate); `grep -c 'parallelFsCacheRead' …` = 5 (:27/:98×2/:108/:111). Verified on disk at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "atomicWriteFile saveCachedModule readCachedFileConcurrently ensureCacheIntegrity getLockfileHash", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt write-rename atomicity, trailing-base64-metadata framing with lastIndexOf parsing, and lockfile-hash wholesale invalidation. Adapt the metadata schema to your transform result shape. Omit the cross-project root-metadata sharing if your host has no per-project cache-dir overrides.
