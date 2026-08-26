<!-- capsule-v2 -->
# Atomic publish + promise-chain lock — how do you make concurrent local byte writes safe and atomic without external lock files?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** two tool executions may target the same output file in one process — how do you serialize them and still guarantee a reader never sees a torn file, even on crash or cancellation?

## withLocalLock mutex + publishLocal choreography
**Path/Symbol:** `src/binary-fs.ts:36 localLocks`, `:38-40 throwIfAborted`, `:42-55 withLocalLock`, `:83-85 isCode`, `:87-124 publishLocal`.
**Signature:** `withLocalLock<T>(path: string, operation: () => Promise<T>): Promise<T>`; `publishLocal(path, displayPath, content, createIfAbsent, mode?: number, signal?): Promise<void>`.
**Data Shape:** module-level `localLocks = Map<string, Promise<unknown>>` keyed by process path; temp file name `.<basename>.<pid>.<uuid>.tmp` in the destination directory.

### Decisive source
```ts
async function withLocalLock<T>(path: string, operation: () => Promise<T>): Promise<T> {
  const prior = localLocks.get(path) ?? Promise.resolve()
  let release!: () => void
  const current = new Promise<void>(resolve => { release = resolve })
  const tail = prior.then(() => current)
  localLocks.set(path, tail)
  await prior
  try {
    return await operation()
  } finally {
    release()
    if (localLocks.get(path) === tail) localLocks.delete(path)
  }
}

async function publishLocal(path, displayPath, content, createIfAbsent, mode, signal?) {
  throwIfAborted(signal)
  const parent = dirname(path)
  await mkdir(parent, { recursive: true })
  const temporary = join(parent, `.${basename(path)}.${process.pid}.${randomUUID()}.tmp`)
  let handle
  try {
    handle = await open(temporary, 'wx', mode ?? 0o600)
    await handle.writeFile(content, signal === undefined ? {} : { signal })
    await handle.sync()
    if (mode !== undefined && process.platform !== 'win32') await handle.chmod(mode)
    await handle.close()
    handle = undefined
    throwIfAborted(signal)
    if (createIfAbsent) {
      try {
        await link(temporary, path)
      } catch (error) {
        if (isCode(error, 'EEXIST'))
          throw new FsError(`cannot overwrite existing "${displayPath}" without reading it first`, 'FS_NOT_OBSERVED', { cause: error })
        throw error
      }
    } else {
      await rename(temporary, path)
    }
  } finally {
    await handle?.close().catch(() => undefined)
    await rm(temporary, { force: true }).catch(() => undefined)
  }
}
```

**Flow:** write request → lock tail chained onto the prior holder for this exact path (FIFO by construction) → inside the lock: exclusive-create temp in the SAME directory as the destination → write → fsync → explicit chmod only when the original file's mode is preserved AND platform ≠ win32 → close → abort re-check → commit via `link` (createIfAbsent: atomic fail-if-exists, EEXIST mapped to typed FS_NOT_OBSERVED with cause preserved) or via `rename` (replace: atomic swap-in) → finally always closes a half-open handle and force-removes any surviving temp.
**Invariant:** readers of the destination see either the complete old file or the complete new file — never partial bytes — because all content lands in the temp and commits in one atomic directory operation; the per-path map entry self-cleans ONLY when this caller still owns the tail (`get(path) === tail`), so a stale release from a superseded waiter cannot delete a newer queue's entry; the pid+UUID temp name makes concurrent processes collision-free without an external lockfile; `wx` on the temp plus `link` for createIfAbsent gives a kernel-enforced existence race check (no TOCTOU between stat and commit); abort is honored twice — before starting and after fsync but before commit — so cancellation can never publish half-acknowledged data; cleanup errors are swallowed (`force:true`, caught close) because the temp is garbage either way.
**Probe:** no dedicated test file exists for binary-fs.ts — recorded block. Deterministic source anchors: direct read of :36-124 this pass confirms every branch; behavioral boundary evidence is `tests/imagegen.spec.ts` write-intent cases exercising publishLocal through writeLocalBytes. Honest caveat: no test drives concurrent same-path writes or crash-mid-publish directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.binary-fs\\.(withLocalLock|publishLocal|isCode|throwIfAborted)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 4, has_more false.

## Verdict
Adopt same-directory exclusive-temp publication with link-vs-rename chosen by intent, tail-chained in-process locks keyed by canonical path, and post-fsync pre-commit abort checks. Adapt the temp-name scheme and whether your intents need the EEXIST→typed-error mapping. Omit cross-process advisory locking when a single process owns the tree, and omit temp files outside the destination directory (cross-device rename breaks atomicity). Coverage: src/binary-fs.ts `no_recorded_issue` + `metadata_match`.
