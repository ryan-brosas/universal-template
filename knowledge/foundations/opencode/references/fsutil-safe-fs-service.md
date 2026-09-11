<!-- capsule-v2 -->
# FSUtil safe filesystem service — how do you wrap platform FS so untrusted callers never see raw errors?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how does a shared filesystem service turn absence and permission failures into values, survive platform quirks (Bun-on-Windows EEXIST), and expose a collect-everything upward walk?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/fs-util.ts`: `FileSystemError` (:14-22), `Interface` (:32-49), layer (:54-199), `node` (:201), pure helpers (:203-260).
**Signature:** `readFileStringSafe(path) => Effect<string | undefined, Error>`; `ensureDir(path) => Effect<void, Error>`; `writeWithDirs(path, content, mode?) => Effect<void, Error>`; `findUp(target, start, stop?)` / `up({targets, start, stop?})` / `globUp(pattern, start, stop?)` => `Effect<string[], Error>`.
**Data Shape:** the service EXTENDS Effect's `FileSystem.FileSystem` — `Service.of({ ...fs, existsSafe, readFileStringSafe, ... })` spreads every platform op through.

### Decisive source
```ts
const readFileStringSafe = Effect.fn("FileSystem.readFileStringSafe")(function* (path: string) {
  return yield* fs.readFileString(path).pipe(
    Effect.catchReason("PlatformError", "NotFound", () => Effect.succeed(undefined)),
    Effect.catchReason("PlatformError", "PermissionDenied", () => Effect.succeed(undefined)),
  )
})
...
yield* fs.makeDirectory(path, { recursive: true }).pipe(
  // Bun on Windows can throw EEXIST here despite recursive mode.
  // https://github.com/oven-sh/bun/issues/21901
  Effect.catchIf(
    (error) => error.reason._tag === "AlreadyExists",
    (error) => isDir(path).pipe(Effect.flatMap((exists) => (exists ? Effect.void : Effect.fail(error)))),
  ),
)
```

**Flow:** safe reads map NotFound AND PermissionDenied to `undefined`/`false` (callers branch on the value, not the error) → JSON parse and directory reads wrap into a typed `FileSystemError{method, cause}` → `ensureDir` swallows AlreadyExists only after re-stat confirms the path is a directory → `writeWithDirs` retries once after `mkdir(dirname, recursive)` when the write fails NotFound → the walk ladder (findUp single-target, up multi-target, globUp glob-per-level with `dot: true` and per-level errors → `[]`) walks `dirname` until `stop` or filesystem root, COLLECTING every hit (not first-match). Pure helpers live outside the layer: `mimeType`, `normalizePath` (win32 realpathSync.native), `windowsPath`, and `contains`/`overlaps` containment checks (consumed by skill-discovery's fail-closed validation).
**Invariant:** absence and permission are VALUES (`undefined`/`false`), never failures; AlreadyExists is swallowed only when a directory really exists there — a file at the same path still fails; the walk stops at `stop` inclusive and never escapes above the filesystem root.
**Probe:** `packages/core/test/filesystem/filesystem.test.ts` (387L: isDir/isFile truth tables, readFileStringSafe undefined-on-missing, readJson FileSystemError on broken JSON, ensureDir idempotent, writeWithDirs creates parents + Uint8Array, findUp start/parent/empty, up multi-target, glob/globMatch, globUp walk, contains/overlaps incl. win32 drive split).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "FSUtil readFileStringSafe ensureDir findUp globUp contains", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the safe-read-to-value mapping and the re-check-before-swallow EEXIST pattern for any shared FS service; adopt the collect-everything walk ladder with an inclusive stop boundary. Adapt the Effect PlatformError reason tags to your host's error taxonomy. Omit the win32-only normalizePath/windowsPath bodies unless porting to Windows. Coverage caveat: `serviceUse(Service)` proxy access and the node wiring (`deps: [filesystem]`) are source-confirmed only; everything else is test-pinned.
