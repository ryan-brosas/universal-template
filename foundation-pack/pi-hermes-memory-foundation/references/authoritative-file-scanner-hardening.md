<!-- capsule-v2 -->
# Authoritative-file scanner hardening — symlink/lstat/canonical-root validation before reading user-editable state

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** A reconciler that scans `projects-memory/*/MEMORY.md` trusts whatever the filesystem presents — how do you refuse symlinked dirs/files and paths that escape their root WITHOUT breaking ENOENT-fast-paths?

## scanProjectDirs + resolveAuthoritativeMemoryFile + isSafeProjectName
**Path/Symbol:** `src/handlers/sync-markdown-memories.ts:scanProjectDirs` (:42–76), `resolveAuthoritativeMemoryFile` (:87–123), `isSafeProjectName` (:125–131), `realpathIfPresent` (:78–85); consumers `syncMarkdownMemoriesToSqlite` (:133–201) and `migrateThenSyncMarkdownMemories` (:203–220).
**Signature:** `resolveAuthoritativeMemoryFile(root, projectName) → string | null`; `isSafeProjectName(name, projectsRoot) → boolean`; `syncMarkdownMemoriesToSqlite(dbManager, globalDir, projectsMemoryDir?, agentRoot?) → BackfillCounters & { projectCount }`.
**Data Shape:** candidate set = union of `projects-memory/<name>/MEMORY.md` and legacy first-level agentRoot folders (excluding global dir name, `projects-memory`, `skills`, dotted names); mirrored-but-unfiled projects are unioned IN from SQLite (`SELECT DISTINCT project …`) so orphans still get reconciled-to-empty.

### Decisive source
```ts
function realpathIfPresent(filePath: string): string {
  try { return fs.realpathSync(filePath); }
  catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return path.resolve(filePath);
    throw error;                       // other errors propagate
  }
}

function resolveAuthoritativeMemoryFile(root: string, projectName: string): string | null {
  const canonicalRoot = realpathIfPresent(root);
  if (!isSafeProjectName(projectName, path.resolve(root))) return null;
  const projectDir = path.join(root, projectName);
  const projectStat = fs.lstatSync(projectDir);            // LSTAT: see the link itself
  if (projectStat.isSymbolicLink() || !projectStat.isDirectory()) return null;
  // ^ a symlinked PROJECT dir is refused, not followed
  const canonicalProjectDir = fs.realpathSync(projectDir);
  if (path.dirname(canonicalProjectDir) !== canonicalRoot) return null;
  // ^ even a real dir whose realpath escapes root (bind mounts, nested links) is refused
  const memoryStat = fs.lstatSync(memoryFile);
  if (memoryStat.isSymbolicLink() || !memoryStat.isFile()) return null;
  const canonicalMemoryFile = fs.realpathSync(memoryFile);
  if (path.dirname(canonicalMemoryFile) !== canonicalProjectDir
      || path.basename(canonicalMemoryFile) !== MEMORY_FILE) return null;
  return canonicalMemoryFile;
}

function isSafeProjectName(name: string, projectsRoot: string): boolean {
  if (!name || name === '.' || name === '..' || name.includes('/') || name.includes('\\')
      || path.isAbsolute(name)) return false;
  const projectDir = path.resolve(projectsRoot, name);
  return path.dirname(projectDir) === projectsRoot && path.basename(projectDir) === name;
}
```

**Flow:** (1) enumerate candidate project names (safe-name filtered); (2) per candidate, validate dir then file through the lstat→realpath→parent-equality chain; (3) reconcile each validated file under its per-file markdown mutation lock, folding counts into shared counters with per-scope warning strings; (4) union in SQLite-known projects so deleting a folder also clears (or empties) its mirror rows.
**Invariant:** ENOENT means "absent ⇒ proceed with the would-be path" while EVERY OTHER stat error propagates — silently swallowing EACCES would masquerade as empty memory; symlinks are rejected at BOTH levels rather than resolved-and-trusted (the scan reads security-sensitive agent memory; following links would let a planted link redirect reconciliation to arbitrary files); name validation is containment-based (resolve-then-compare against the root), not regex-based.
**Probe:** `tests/handlers/sync-markdown-memories.test.ts` — asserts symlinked project dirs and memory files return null, escaped realpaths are refused, missing dirs yield the canonical join, and mirrored-only projects are reconciled. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "resolveAuthoritativeMemoryFile isSafeProjectName scanProjectDirs", limit: 5 })`

## Verdict
Adopt this validation chain verbatim wherever you enumerate and read user-writable state files. Adapt reserved-name lists and the root path. The lstat-refuse (not resolve-trust) posture plus ENOENT-vs-propagate split is the part porters get wrong.
