<!-- capsule-v2 -->
# directory_tree exclude patterns — what is the three-minimatch grammar that decides whether a file OR a whole subtree disappears from a recursive walk?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** How are user-supplied exclude patterns interpreted against ROOT-RELATIVE paths so `.env` hides while `.env.local` and nested `node_modules` behave correctly?

## Per-entry: glob-direct OR `**/<pat>` OR `**/<pat>/**`, matched with `{dot: true}` on relative paths
**Path/Symbol:** `src/filesystem/index.ts` `directory_tree` handler's internal `buildTree` (recursive readdir); logic mirrored verbatim in the test double `buildTreeForTesting` — direct test `src/filesystem/__tests__/directory-tree.test.ts` (whole file, 146L: mirror implementation :16–49; fixture tree incl. `nested/node_modules` :54–70; seven behavior pins :76–146).

**Signature:** `shouldExclude = excludePatterns.some(pattern => pattern.includes('*') ? minimatch(relPath, pattern, {dot:true}) : minimatch(relPath, pattern, {dot:true}) || minimatch(relPath, '**/'+pattern, {dot:true}) || minimatch(relPath, '**/'+pattern+'/**', {dot:true}))` where `relPath = path.relative(rootPath, entryAbsPath)`.

**Data Shape:** recursion emits `TreeEntry { name, type: 'file'|'directory', children? }`; excluded entries are OMITTED (not stubbed), so exclusion of a dir prunes its entire subtree naturally.

### Decisive source
```ts
// __tests__/directory-tree.test.ts:21-31 — root-RELATIVE paths + the triple-match fallback
const relativePath = path.relative(rootPath, path.join(currentPath, entry.name));
const shouldExclude = excludePatterns.some(pattern => {
  if (pattern.includes('*')) {
    return minimatch(relativePath, pattern, {dot: true});
  }
  // For files: match exact name or as part of path
  // For directories: match as directory path
  return minimatch(relativePath, pattern, {dot: true}) ||
         minimatch(relativePath, `**/${pattern}`, {dot: true}) ||
         minimatch(relativePath, `**/${pattern}/**`, {dot: true});
});
```

**Flow:** readdir(withFileTypes) at current level → compute each entry's path RELATIVE TO THE WALK ROOT → test the triple match → excluded ⇒ skip (subtree never entered) → directories recurse with the SAME root for rel-path stability → assemble nested result.

**Invariants:**
1. **Match against root-relative, not absolute, paths** — absolute matching breaks pattern portability across mount points and makes `nested/node_modules` unmatchable by bare names.
2. **`{dot: true}` is load-bearing**: dotfiles (`.env`, `.git`) must be matchable; without it, every hidden-dir exclusion silently fails.
3. **Bare-name patterns get the `**/` fallbacks**: `'node_modules'` must exclude BOTH top-level and `nested/node_modules` (pinned :96–107) — plain minimatch of a relative path would only catch the top level.
4. **`*.env` ≠ prefix match**: it must hide `.env` but NOT `.env.local` (:109–116) — glob semantics, not string startsWith.
5. Empty pattern list excludes nothing (:137–146).

**Probe:** `__tests__/directory-tree.test.ts` IS the probe (tempdir fixture + 7 assertions). Coverage caveat: the production `buildTree` is exercised indirectly via the mirrored logic (test comment :6–8 acknowledges the extraction); symlink cycles untested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "directory_tree buildTree exclude minimatch relative dot", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the relative-path + triple-match + dot-aware grammar wherever recursive listings take user exclusions; adapt the TreeEntry shape to your output schema (string-typed per `tool-output-schema-dual-emission.md`); omit the test-mirror duplication by extracting buildTree into an importable unit in your port.
