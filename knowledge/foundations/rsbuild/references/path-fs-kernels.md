<!-- capsule-v2 -->
# path/fs helper kernels — why does dedupeNestedPaths sort by LENGTH and emptyDir treat .git as emptiness?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the small pure kernels every other module leans on.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/helpers/path.ts` — toRelativePath 5–15 ('' → './'), getCommonParentPath 17–36, getCompiledPath 38, ensureAbsolutePath 47–48, getPathnameFromUrl 50–56, `dedupeNestedPaths` 59–70, toPosixPath 77–82, normalizeRuleConditionPath 89–102 (Windows require.resolve posix→backslash); `helpers/fs.ts` — isFileSync throwIfNoEntry 7–13, `isEmptyDir` 15–18 ('.git'-only counts as EMPTY), findExists 25–32, fileExistsByCompilation 48–65, readFileAsync 70–87, emptyDir 89–128.
**Signature:** `dedupeNestedPaths(paths: string[]): string[]`; `getCommonParentPath(paths: string[]): string`.
**Data Shape:** all kernels pure/synchronous except fs async trio; Windows handled at BOTH layers (sep vs posix).

### Decisive source
```ts
export const dedupeNestedPaths = (paths: string[]): string[] =>
  paths
    .sort((p1, p2) => (p2.length > p1.length ? -1 : 1))   // shortest first: parents precede children
    .reduce<string[]>((prev, curr) => {
      const isSub = prev.find((p) => curr.startsWith(p) || curr === p);
      if (isSub) return prev;
      return prev.concat(curr);
    }, []);
```
```ts
export function isEmptyDir(path: string): boolean {
  const files = fs.readdirSync(path);
  return files.length === 0 || (files.length === 1 && files[0] === '.git');   // fresh `git init` counts as empty project
}
```

**Flow:** sort-by-length makes the reduce's startsWith check sufficient — no path-separator edge cases because parents were seen first. getCommonParentPath splits on sep and compares segment-wise (not char-wise) so `/foo/bar` vs `/foo/baz` share `/foo` not `/foo/ba`. normalizeRuleConditionPath converts ONLY absolute windows paths containing forward slashes — the exact shape require.resolve returns.
**Invariant:** (1) length-sort must be stable-ish ascending or nested dedupe silently keeps the child and drops the parent; (2) isEmptyDir's .git exemption drives scaffold-into-existing-repo flows — removing it breaks create-* tools; (3) readFileAsync must distinguish err from undefined-data (both possible).
**Probe:** unit `packages/core/tests/helpers.test.ts:5/:234/:243/:247` (dedupeNestedPaths + getCommonParentPath tables).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "dedupeNestedPaths getCommonParentPath isEmptyDir findExists normalizeRuleConditionPath", limit: 8 });
```

## Verdict
Adopt these kernels verbatim (adapt sep handling). They are the substrate every seam above assumes. Omit nothing — each has a pinned consumer.
