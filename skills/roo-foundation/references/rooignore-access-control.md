<!-- capsule-v2 -->
# RooIgnore access control — how do you enforce .gitignore-style denial across tools AND terminal commands without locking yourself out?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you gate file reads, listings, and shell commands on an ignore file, with symlink resolution and fail-direction chosen per surface?

## Hot-reloaded ignore instance; realpath-then-relative checks; per-surface fail direction
**Path/Symbol:** `src/core/ignore/RooIgnoreController.ts` (class :15-213; watcher :38-56; `loadRooIgnore` load+self-ignore `.rooignore` add :64-80; `validateAccess` :89-113; `validateCommand` :123-170; `filterPaths` :179-185 fail-CLOSED; `getInstructions` :206-213).
**Signature:** `constructor(cwd: string)` (starts watcher) → `await initialize()` before use; `validateAccess(filePath): boolean`; `validateCommand(command): string | undefined` (**returns the offending path**, undefined = allowed).
**Data Shape:** `.rooignore` gitignore-syntax content; the ignore file ITSELF is always added as ignored (`ignoreInstance.add(".rooignore")`).

### Decisive source
```ts
// validateAccess: resolve symlinks FIRST so ignoring a real path catches symlink aliases
try { realPath = fsSync.realpathSync(path.resolve(this.cwd, filePath)) }
catch { realPath = absolutePath }                        // broken link → judge literal path
const relativePath = path.relative(this.cwd, realPath).toPosix()
return !this.ignoreInstance.ignores(relativePath)
// ...but ANY throw in validateAccess returns TRUE (allow) — read-path is fail-open for UX

// filterPaths (bulk listings) flips the convention:
} catch (error) { return [] }   // "Fail closed for security"
```
`loadRooIgnore()` rebuilds a FRESH `ignore()` instance on every change event (create/change/delete watched) — mutating an existing instance would duplicate patterns. `validateCommand` whitelists file-READING commands (`cat less more head tail grep awk sed get-content gc type select-string sls`) and checks only non-flag args (skipping `-x`, `/flags`, PowerShell `:`-params); `getInstructions()` exposes the patterns to the model with a 🔒 marker legend so blocked files are legible rather than mysterious.

**Flow:** construct + watch → initialize loads patterns → every tool surface calls validateAccess/filterPaths → ExecuteCommand consults validateCommand and reports the first offending argument.
**Invariant:** The controller never locks out its own configuration file; pattern reloads are full-instance replacements; symlinked paths are judged by their TARGET; fail direction is a deliberate PER-SURFACE decision (single-read allow-on-error vs listing deny-on-error).
**Probe:** `src/core/ignore/__tests__/RooIgnoreController.security.spec.ts` (:59 Unix readers blocked, :85 PowerShell readers, :147 path-traversal attempts, :302 filterPaths fails closed); functional twin `RooIgnoreController.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "RooIgnoreController validateAccess validateCommand filterPaths", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt realpath-before-match, self-exclusion, fresh-instance-per-reload, and the documented split fail directions. Adapt the reader-command whitelist to your shells. Do not unify the two fail directions — they encode different threat models (UX recovery vs enumeration safety).
