<!-- capsule-v2 -->
# cleanDistPath safety gates — why is 'auto' a strict-subdir test plus writeToDisk check?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce when emptying dist is allowed, the keep-regex passthrough, and the Rsbuild-outputs extra target.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/cleanOutput.ts` — `isStrictSubdir` 14–18 (trailing-sep normalize), `normalizeCleanDistPath` 20–36, rsbuild-outputs path 48–60, per-env decision 62–90+; executor `helpers/fs.ts` `emptyDir` 89–128 (keep posix-tested, keep-length guards rmdir).
**Signature:** `emptyDir(dir, logger, keep: RegExp[] = [], checkExists = true): Promise<void>`.
**Data Shape:** output.cleanDistPath: boolean | 'auto' | {enable, keep?: RegExp[]}.

### Decisive source
```ts
const isStrictSubdir = (parent, child) => {
  const parentDir = addTrailingSep(parent), childDir = addTrailingSep(child);
  return parentDir !== childDir && childDir.startsWith(parentDir);
};
if (enable === 'auto') {
  if (isDev && !config.dev.writeToDisk) return undefined;   // nothing on disk → nothing to clean
  if (isStrictSubdir(rootPath, distPath)) return { path: distPath, keep };
  api.logger.warn('The dist path is not a subdir of root path, Rsbuild will not empty it.'); ... return undefined;
}
```
```ts
// helpers/fs.ts emptyDir:
if (keep.length) { const posixFullPath = toPosixPath(fullPath); if (keep.some((regex) => regex.test(posixFullPath))) return; }
if (entry.isDirectory()) { await emptyDir(fullPath, logger, keep, false); if (!keep.length) await fs.promises.rmdir(fullPath); }
```

**Flow:** enable:true forces cleaning regardless of location (user owns the risk); 'auto' cleans only inside the project and only when files actually hit disk. The plugin ALSO cleans `<dist>/.rsbuild/` (inspected configs etc.) under the same gate. Recursion keeps matched FILES but won't prune their parent dirs when keep is active — preserving directory structure of kept assets.
**Invariant:** (1) trailing-sep normalization must precede startsWith or `/root/dist-extra` falsely matches `/root/dist`; (2) rmdir only when !keep.length — with keep rules, empty dirs may hold kept-file siblings later; (3) all failures inside emptyDir degrade to debug logs — cleaning must never fail a build.
**Probe:** unit snapshot coverage via config normalization suites; e2e output-clean cases. Direct unit suite absent for isStrictSubdir edge table (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginCleanOutput isStrictSubdir emptyDir dedupeNestedPaths", limit: 8 });
```

## Verdict
Adopt strict-subdir gating, dev-writeToDisk suppression, posix-normalized keep regexes, and fail-open cleanup. Adapt warn copy to host. Omit .rsbuild outputs path if host has no inspector.
