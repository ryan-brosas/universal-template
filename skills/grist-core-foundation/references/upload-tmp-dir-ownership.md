<!-- capsule-v2 -->
# Tmp dir ownership wrapper — why does cleanupCallback remove the directory ITSELF and then still call the library's callback?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact contract of the tmp-dir handle handed to upload registrations so that double-deletes, symlink traps, and atexit ghosts are all impossible?

## fse.remove + original cb swallowed — realpath BEFORE use; unsafeCleanup always on
**Path/Symbol:** `app/server/lib/uploads.ts` — `createTmpDir(options)` (:402–433); consumed by `handleOptionalUpload` (:208), `_fetchURL` (:476), `moveUpload` (:385).
**Signature:** `createTmpDir(options: tmp.DirOptions): Promise<{tmpDir: string, cleanupCallback: CleanupCB}>` with `CleanupCB = () => void | Promise<void>`.
**Data Shape:** defaults `{prefix: "grist-upload-", unsafeCleanup: true}` spread UNDER caller options; returns REALPATH-resolved dir string.

### Decisive source
```ts
const fullOptions = { prefix: "grist-upload-", unsafeCleanup: true, ...options };
const [tmpDir, tmpCleanup] = await fromCallback((cb) => tmp.dir(fullOptions, cb), { multiArgs: true });
// The `tmp` library sometimes forcibly resolves the path,
// doing it here makes it predictable behaviour and resistant to library behaviour changes.
const realTmpDir = await fse.realpath(tmpDir);
async function cleanupCallback() {
  await fse.remove(realTmpDir);        // async removal FIRST
  try { await tmpCleanup(); }          // then tell `tmp` to forget it (may throw if already gone)
  catch (err) { /* OK if it fails because the dir is already removed. */ }
}
return { tmpDir: realTmpDir, cleanupCallback };
```

**Flow:** caller needs scratch space → `tmp.dir` makes it → realpath resolves OS temp symlinks (`/var` vs `/private/var`, `/tmp` aliasing) ONCE up front → every later consumer compares/moves against that canonical path → cleanup removes the tree with async fs-extra, then invokes the library's own callback inside a swallowing try so `tmp`'s internal exit registry doesn't retry a vanished dir.
**Invariant:** the resolved path is the single identity used everywhere downstream (`isPathWithin` checks in `moveUpload`, sandbox path grants) — mixing raw and realpath forms breaks containment comparisons; `unsafeCleanup: true` is mandatory for dirs containing open/being-written files; cleanup must be IDEMPOTENT because both the inactivity timer and explicit `cleanup()` can race toward it — second call finds nothing and must not throw; the swallowed inner-callback error is deliberate, not sloppy.
**Probe:** `test/server/lib/uploads.ts` (:20–42 create with prefix/postfix → file survives until cleanupCallback → both file and dir gone after).
**Caveat:** runner-blocked here; probe recorded as pinned assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "createTmpDir realpath unsafeCleanup prefix grist-upload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: realpath-at-creation as canonical identity, remove-then-forget idempotent cleanup pair. Adapt prefix naming and option surface to your stack. Omit any reliance on the temp-library's automatic atexit for signal-killed processes — grist explicitly registers its own shutdown hook because that mechanism dies with SIGTERM/SIGINT (see `upload-lifecycle-inactivity-gc.md`).
