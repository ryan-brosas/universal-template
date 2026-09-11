<!-- capsule-v2 -->
# glob ignore-utils — how does a flat pattern list decide "this path lives under an ignored directory"?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Why does this hand-rolled checker exist next to real glob machinery, and what are its exact match rules?

## Two-pass segment matcher over DIRS_TO_IGNORE
**Path/Symbol:** `src/services/glob/ignore-utils.ts:isPathInIgnoredDirectory` (whole file, lines 10–45); patterns from `./constants:DIRS_TO_IGNORE`.
**Signature:** `function isPathInIgnoredDirectory(filePath: string): boolean`.
**Data Shape:** input is any path (Windows separators normalized `\ → /`); `DIRS_TO_IGNORE` is a plain string array whose ONLY magic entry is the literal `".*"` meaning "any dot-directory".

### Decisive source
```ts
// Handle the ".*" pattern for hidden directories
if (DIRS_TO_IGNORE.includes(".*") && part.startsWith(".") && part !== ".") {
    return true
}
// Check for exact matches
if (DIRS_TO_IGNORE.includes(part)) { return true }
…
// Check if the directory appears in the path
if (normalizedPath.includes(`/${dir}/`)) { return true }
```

**Flow:** split on `/`; pass 1 walks segments — skip empties, hidden-dir rule (`.*` present in list + segment starts with `.` and isn't bare `.`), then exact whole-segment equality; pass 2 scans remaining non-magic patterns as `/dir/` substrings of the normalized path. Any hit → true.
**Invariant:** matching is EXACT SEGMENT or substring-with-slashes — no glob semantics at all (`node_modules` matches but `node*` would not; a pattern like `build` also matches `sub/build/x` via pass 2). The `".*"` rule deliberately ignores `.gitignore`-style negation and matches EVERY hidden directory including `.roo`, `.env` dirs — callers that need hidden dirs visible must not have `.*` in their list. Bare `.` and `..`-style parts are only partially special-cased (`.` skipped by the startsWith guard's `!== "."`).
**Probe:** `grep -cF 'DIRS_TO_IGNORE.includes(".*")' src/services/glob/ignore-utils.ts` → 1; `grep -c 'startsWith(".")' src/services/glob/ignore-utils.ts` → 1; `grep -c 'normalizedPath.includes(`/\${dir}/`)' src/services/glob/ignore-utils.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "isPathInIgnoredDirectory DIRS_TO_IGNORE", limit: 10 });
```

## Verdict
Adopt for cheap pre-glob filtering where full gitignore semantics are unnecessary; do NOT substitute it where negation or anchored patterns matter. Adapt the magic `.*` convention to your host (or replace with picomatch). Coverage caveat: no direct spec at pin (`src/services/glob/__mocks__/list-files.ts` is a test MOCK, not a spec); pinned via source read + greps.
