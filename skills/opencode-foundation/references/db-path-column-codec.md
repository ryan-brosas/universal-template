<!-- capsule-v2 -->
# DB path column codec — how do you store Windows paths in SQLite without breaking POSIX rows?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how do Drizzle custom column types normalize Windows paths to a canonical storage form at the driver boundary while keeping legacy empty values and POSIX backslash-in-filename rows byte-identical?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/database/path.ts`: `storagePath` (:5-9), `isWindowsStoragePath` (:11-13), `absolute` (:15-21), `toPlatform` (:23-27), `absoluteColumn` (:29-45), `directoryColumn` (:47-61), `pathColumn` (:63-73), `absoluteArrayColumn` (:75-91).
**Signature:** `absoluteColumn: CustomType<{data: AbsolutePath, driverData: string}>`; `directoryColumn: CustomType<{data: string}>` (legacy-empty tolerant); `pathColumn: CustomType<{data: string}>` (relative); `absoluteArrayColumn: CustomType<{data: AbsolutePath[]}>` (JSON).
**Data Shape:** storage form = forward slashes; win32 drive form `^[A-Za-z]:/` or UNC `//` marks a windows-shaped value.

### Decisive source
```ts
function storagePath(input: string) {
  if (process.platform !== "win32") return input
  return input.replaceAll("\\", "/")
}
function absolute(input: string) {
  const result = storagePath(input)
  if (!nodePath.posix.isAbsolute(result) && !(process.platform === "win32" && isWindowsStoragePath(result))) {
    throw new Error(`Path is not absolute: ${input}`)
  }
  return result
}
```
```ts
// Legacy sessions may persist an empty directory. Keep that existing value
// readable while normalizing and validating every real directory.
toDriver(input) { return input ? absolute(input) : input },
fromDriver(input) { return input ? toPlatform(absolute(input)) : input },
```

**Flow:** write path — `storagePath` converts backslashes to slashes ONLY on win32, `absolute()` validates posix-absolute OR (on win32) drive/UNC shape and throws "Path is not absolute" otherwise, arrays serialize as JSON of validated paths → read path — `fromDriver` validates again and `toPlatform` converts back to backslashes ONLY on win32 for windows-shaped values. `pathColumn` (relative paths) applies `storagePath` in both directions without the absolute check.
**Invariant:** normalization is platform-gated, not data-gated — on POSIX a backslash is a legal filename character and must survive byte-for-byte (test pins `/home/me/we\ird` unchanged); the `/` worktree sentinel survives; a non-absolute value in an absolute column throws at the driver boundary, not deep in business logic.
**Probe:** `packages/core/test/database-migration.test.ts` ("normalizes Windows storage paths and leaves POSIX paths untouched" — drive, UNC, `/` sentinel, and POSIX-backslash rows; "maps native Windows paths through database columns" (win32-only) — insert/select/update round-trips through `ProjectTable`/`SessionTable` incl. rejecting `AbsolutePath.make("not-absolute")`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "absoluteColumn directoryColumn pathColumn storagePath toPlatform", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the platform-gated normalize-on-write/restore-on-read codec with validation at the driver boundary. Adapt the storage form (forward slashes) and the windows-shape predicate to your path model. Omit `absoluteArrayColumn` if you store no path arrays. Coverage caveat: the win32 round-trip test is skipped on non-Windows hosts; the POSIX-preservation half runs everywhere.
