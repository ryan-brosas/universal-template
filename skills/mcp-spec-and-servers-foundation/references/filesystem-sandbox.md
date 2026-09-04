<!-- capsule-v2 -->
# Filesystem sandbox — how does the reference filesystem server make path containment symlink-proof and race-proof?

**Source:** modelcontextprotocol/servers MIT `main@76d64c8`; Codebase Memory `servers`. **Question:** What is the validation chain that stops traversal, prefix-collision, and symlink-swap escapes — including for files that don't exist yet?

## Containment → realpath → parent-of-new-file, then wx-flag atomic writes
**Path/Symbol:** `src/filesystem/lib.ts:validatePath` (:99–140); boundary predicate `src/filesystem/path-validation.ts:isPathWithinAllowedDirectories` (:11–86); startup allowlist `src/filesystem/index.ts` (:45–93 — stores BOTH original and `fs.realpath`-resolved paths to survive macOS `/tmp → /private/tmp`); write primitive `lib.ts:writeFileContent` (:161–185).

**Signature:** `async validatePath(requestedPath: string): Promise<string>`; `isPathWithinAllowedDirectories(absolutePath: string, allowedDirectories: string[]): boolean`.

### Decisive source
```ts
// src/filesystem/lib.ts:107-139 — three-stage chain, verbatim order:
// Security: Check if path is within allowed directories before any file operations
const isAllowed = isPathWithinAllowedDirectories(normalizedRequested, allowedDirectories);
if (!isAllowed) throw new Error(`Access denied - path outside allowed directories: ...`);
// Security: Handle symlinks by checking their real path to prevent symlink attacks
try {
  const realPath = await fs.realpath(absolute);
  if (!isPathWithinAllowedDirectories(normalizePath(realPath), allowedDirectories))
    throw new Error(`Access denied - symlink target outside allowed directories: ...`);
  return realPath;                       // operate on the REAL path
} catch (error) {
  if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
    // New files: verify the PARENT's real path instead
    const parentDir = path.dirname(absolute);
    const realParentPath = await fs.realpath(parentDir);
    if (!isPathWithinAllowedDirectories(normalizePath(realParentPath), allowedDirectories))
      throw new Error(`Access denied - parent directory outside allowed directories: ...`);
    return absolute;
  }
  throw error;
}
```
Boundary predicate details (path-validation.ts): rejects null bytes and relative leftovers; normalizes BOTH sides with `path.resolve(path.normalize(x))`; containment test is `p === dir || p.startsWith(dir + path.sep)` — the trailing separator kills the prefix vulnerability where `/allowed/project2` would otherwise pass a naive `/allowed/project`.startsWith check (test :63–70 pins `project2`, `project_backup`, `project-old`, `projectile`, `project.bak` all rejected). Writes (`lib.ts:161–185`): try `flag:'wx'` exclusive create first — fails through pre-existing symlinks; on EEXIST write to `${filePath}.${randomBytes(16).hex}.tmp` then atomic `fs.rename` (rename replaces atomically and does not follow symlinks); unlink temp on rename failure.

**Flow:** expandHome → absolute-or-resolve-against-first-allowlist-dir → normalize → textual containment → realpath re-check (or parent re-check for ENOENT) → caller operates on returned REAL path. Startup additionally drops non-directory/inaccessible entries but exits 1 only when ALL specified dirs are inaccessible (:69–88).

**Invariant:** every file operation validates against REAL resolved paths, never the requested spelling — a porter who checks only the lexical path loses to `ln -s /etc allowed/link`; a porter who skips the ENOENT-parent branch lets new files land anywhere writable via dangling symlinks.

**Probe:** `src/filesystem/__tests__/path-validation.test.ts::"blocks similar directory names (prefix vulnerability)"` (:63), `::"blocks paths outside allowed directories"` (:72), `::"rejects empty inputs"` (:111), `::"handles unicode characters in paths"` (:196+); `lib.test.ts` covers formatSize/applyFileEdits; graph TESTS edges confirm the pair (`search_graph --name-pattern isPathWithinAllowedDirectories`).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "validatePath isPathWithinAllowedDirectories symlink realpath allowed directories", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.trace_path({ project: "servers", function_name: "servers.src.filesystem.lib.validatePath", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the containment→realpath→parent chain, sep-terminated startsWith boundary, dual original/resolved allowlists, and wx-then-atomic-rename writes; adapt the allowlist source (CLI args vs MCP roots) and error copy to your host; omit the git-style diff preview of applyFileEdits unless you need dry-run edits.
