<!-- capsule-v2 -->
# Cross-platform tree kill — how do you force-kill a spawned process and its children synchronously on Windows and POSIX?

**Source:** playwright (microsoft/playwright) Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** How do you write ONE kill routine that (a) may be called from a synchronous process-'exit' handler, (b) kills the whole child tree, and (c) is idempotent after the process already died?

## Sync killProcess + platform fork + sync cleanup twin
**Path/Symbol:** `packages/utils/processLauncher.ts:killProcess` (lines 225-252) and `killProcessAndCleanup` (lines 254-265).
**Signature:** `function killProcess(): void` — deliberately **not** async ("This method has to be sync to be used in the 'exit' event handler"); `killProcessAndCleanup(): void`.
**Data Shape:** Guards on the triple `spawnedProcess.pid && !spawnedProcess.killed && !processClosed`; kill exceptions are swallowed ("the process might have already stopped").

### Decisive source
```ts
if (spawnedProcess.pid && !spawnedProcess.killed && !processClosed) {
  try {
    if (process.platform === 'win32') {
      const taskkillProcess = childProcess.spawnSync(`taskkill /pid ${spawnedProcess.pid} /T /F`, { shell: true, windowsHide: true });
      ...
    } else {
      process.kill(-spawnedProcess.pid, 'SIGKILL');   // negative pid = process group
    }
  } catch (e) { /* the process might have already stopped */ }
}
// Sync cleanup twin for exit handlers:
for (const dir of options.tempDirectories) {
  try { fs.rmSync(dir, { force: true, recursive: true, maxRetries: 5 }); } catch {}
}
```

**Flow:** unregister from global sets → drop shared signal handlers if last → log `<kill>` → guard-check → Windows: `taskkill /T /F` (tree+force) via sync spawn; POSIX: SIGKILL to `-pid` (works only because spawn used `detached:true`, making the child a group leader). The async path (`killAndWait`) wraps this plus `waitForCleanup` so ordinary callers await death + temp-dir removal.
**Invariant:** The kill itself must stay synchronous (usable inside `process.on('exit')`); it must be safe to call twice or after natural death; and both a sync (`rmSync`) and an async (`removeFolders`) temp-dir cleanup must exist because exit handlers can't await.
**Probe:** `tests/library/browsertype-launch.spec.ts` exercises kill paths indirectly via close/timeout tests (:78-96); `tests/config/commonFixtures.ts:164-231` mirrors the same negative-pid/taskkill technique in its own test-infra `killProcessGroup`. No direct unit test for killProcess — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "killProcess taskkill SIGKILL process group", limit: 10 });
// resolves killProcess (226-252), killProcessAndCleanup (254-265), tests/config/commonFixtures.killProcessGroup
```

## Verdict
Adopt the sync-kill contract, the win32-taskkill/POSIX-negative-pid fork, the idempotence guards, and the dual sync/async cleanup twins. Adapt the Windows command line and retry counts to your host. Omit Playwright's pid-tagged kill logging if you log elsewhere.
