<!-- capsule-v2 -->
# Workspace watcher degrade-to-empty — vcs-gated root watch plus HEAD-only .git watch

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how do you watch a workspace for file changes without watching git internals, and what happens on every failure path?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/filesystem/watcher.ts`: `watcher()` lazy binding (:36-48), layer body (:63-140), `subscribe` (:92-102), `.git` subscription (:118-131).
**Signature:** `Service = "@opencode/v2/FileWatcher"` with an EMPTY interface (`{}`) — all behavior is event publication; `Event = FileSystemWatcher.Event` (Updated: `{file, event: "add"|"change"|"unlink"}`).
**Data Shape:** `@parcel/watcher` per-platform binding required lazily (linux binding name carries a glibc/musl libc suffix); subscriptions tracked in an array with one global unsubscribe finalizer; `SUBSCRIBE_TIMEOUT_MS = 10_000`.

### Decisive source
```ts
if (location.vcs && (yield* Flag.OPENCODE_EXPERIMENTAL_FILEWATCHER)) {
  yield* Effect.forkScoped(
    subscribe(location.directory, [...Ignore.PATTERNS, ...config, ...protecteds(location.directory)]),
  )
}
if (location.vcs?.type === "git") {
  const resolved = (yield* git.repo.discover(location.directory))?.gitDirectory
  const vcs = resolved ? yield* fs.realPath(resolved).pipe(Effect.catch(() => Effect.succeed(resolved))) : undefined
  if (vcs && !config.includes(".git") && !config.includes(vcs) && (!resolved || !config.includes(resolved))) {
    const ignore = (yield* fs.readDirectoryEntries(vcs).pipe(Effect.catch(() => Effect.succeed([]))))
      .flatMap((entry) => (entry.name === "HEAD" ? [] : [entry.name]))
    yield* Effect.forkScoped(subscribe(vcs, ignore))
  }
}
```

**Flow:** every degradation path returns an empty service: experimental-disable flag, unsupported platform backend, missing native binding, and any init error (outer `catchCause` → logError + empty service). When live: the workspace root is subscribed ONLY if a vcs root exists AND the experimental filewatcher flag is set, ignoring Ignore.PATTERNS + config `watcher.ignore` + Protected.paths() filtered to inside the directory; separately, the REAL .git directory (symlink-resolved via realPath) is subscribed ignoring every entry except HEAD — so branch switches publish but index churn does not. Updates are published to EventV2 via `runForkWith(context)` (fire-and-forget fibers over the captured context). `subscribe` wraps the native promise with a 10s timeout and unsubscribes on failure; the layer finalizer unsubscribes everything.
**Invariant:** watcher failure never fails the app (empty service everywhere); `.git/HEAD` events flow while `.git/index` and other internals do not; a non-git root produces no root subscription at all.
**Probe:** `packages/core/test/filesystem/watcher.test.ts` (native-binding-gated suite: add/change/unlink publication, non-git roots stay silent, cleanup stops events, `.git/index` ignored, `.git/HEAD` published, symlinked `.git` resolves to the real path). `describeWatcher` skips when the native binding is absent or CI is set — a recorded coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "opencode", query: "Watcher subscribe gitDirectory HEAD ignore EventV2 publish", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the degrade-to-empty posture for optional platform capabilities and the two-subscription shape (workspace root with ignore lists + git-dir with everything-but-HEAD) for any git-aware watcher. Adapt the ignore sources to your config grammar. Omit the symlink realPath resolution if your host cannot create symlinked git dirs. Coverage caveat: the test suite self-skips without the native binding — on such hosts the capsule is source-confirmed only.
