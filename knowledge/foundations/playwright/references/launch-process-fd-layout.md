<!-- capsule-v2 -->
# Launch-process fd layout & closure registry — how do you spawn a browser child so its whole tree is killable and it speaks on fds 3/4?

**Source:** playwright (microsoft/playwright) Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** When spawning a long-lived browser/tool process, which stdio layout, detach mode, and global registration make later tree-kill and cleanup possible without unhandled 'error' events or leaked temp dirs?

## Spawn → registered closures → close-event teardown
**Path/Symbol:** `packages/utils/processLauncher.ts:launchProcess` (lines 131-273, registry at 51-56, close handler 185-194).
**Signature:** `launchProcess(options: LaunchProcessOptions): Promise<{ launchedProcess: ChildProcess, gracefullyClose(): Promise<void>, kill(): Promise<void> }>` with `options.stdio: 'pipe' | 'stdin'`, `tempDirectories: string[]`, `attemptToGracefullyClose(): Promise<any>`, `onExit(code, signal)`.
**Data Shape:** For `'pipe'`, stdio is **five** entries — `['ignore','pipe','pipe','pipe','pipe']`: stdin ignored, stdout/stderr logged via readline, **fd 3/4 are the protocol pipe**. On POSIX `detached: true` makes the child a process-group leader so a later `process.kill(-pid)` reaches the whole tree.

### Decisive source
```ts
const stdio: ('ignore' | 'pipe')[] = options.stdio === 'pipe' ? ['ignore', 'pipe', 'pipe', 'pipe', 'pipe'] : ['pipe', 'pipe', 'pipe'];
const spawnedProcess = childProcess.spawn(options.command, options.args || [], {
  // detached makes child a leader of a new process group, making it possible to kill
  // child process tree with `.kill(-pid)`.
  detached: process.platform !== 'win32', ... });
// Prevent Unhandled 'error' event.
spawnedProcess.on('error', () => {});
if (!spawnedProcess.pid) { /* failedPromise resolved by once('error') -> await cleanup(); throw */ }
...
gracefullyCloseSet.add(gracefullyClose);
killSet.add(killProcessAndCleanup);
```
The failure path needs BOTH listeners: the no-op handler stops the crash; the `once('error')` one converts it into `'Failed to launch: ' + error` and still runs temp-dir `cleanup()` before rethrowing.

**Flow:** spawn → register closures into module-level `gracefullyCloseSet`/`killSet` → on `'close'`: set `processClosed`, delete both registrations, drop now-unneeded process handlers, call `onExit`, then run async temp-dir cleanup and resolve `waitForCleanup` → every waiter (close/kill) unblocks.
**Invariant:** A spawned process must never be unregistered from the global kill sets before its `'close'` event fires, or a process-exit handler will leak it; conversely nothing may stay registered after `'close'`.
**Probe:** `tests/library/browsertype-launch.spec.ts:72-76` (`should reject if executable path is invalid`) pins the failed-spawn path: launching with `executablePath: 'random-invalid-path'` rejects with a message containing `Failed to launch`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", query: "launchProcess gracefullyCloseSet stdio pipe", limit: 10 });
// resolves launchProcess (packages/utils/processLauncher.ts 131-273), gracefullyCloseAll (54-56)
```

## Verdict
Adopt the five-fd layout (protocol on fd3/4), POSIX `detached:true` + negative-pid group kill, dual error-listener spawn-failure conversion, and the global close/kill registries as portable contracts. Adapt fd indices to your transport's expectations and the temp-dir policy to your host. Omit Playwright's readline-based stdout log tagging if you have structured logging. Caveat: no dedicated upstream unit test for processLauncher.ts itself; behavior pinned indirectly by library suites.
