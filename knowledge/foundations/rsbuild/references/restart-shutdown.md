<!-- capsule-v2 -->
# Restart & shutdown — how do restart requests run cleanups exactly-once and keep the process exit paths safe?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the cleanup-set swap during requestRestart, why a throwing cleanup must not block the rest nor leak into the next round, and the SIGINT sole-listener exit rule.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/helpers/restartManager.ts:createRestartManager` (15–70); `packages/core/src/restart.ts:requestRestart` (19–48), `watchFilesForRestart` (50–174); `helpers/exitHook.ts` (11–55); `server/gracefulShutdown.ts` (11–69).
**Signature:** `createRestartManager({onRestart, restart?}): RestartManager`; `exitHook(cb): () => void`; `setupGracefulShutdown(): () => void`.
**Data Shape:** `cleanups: Set<Cleanup>` swapped by reference; RestartContext `{action:'dev'|'build', options, filePath?, event?}`.

### Decisive source
```ts
async requestRestart(context) {
  if (!restart) { await onRestart(context); return false; }   // no executor → notify-only, report failure
  const currentCleanups = cleanups;
  cleanups = new Set();                                        // SWAP FIRST: later registrations belong to next life
  let hasError = false; let firstError: unknown;
  try { await onRestart(context); } catch (e) { hasError = true; firstError = e; }
  for (const cleanup of currentCleanups) {
    try { await cleanup(); }
    catch (e) { if (!hasError) { hasError = true; firstError = e; } }   // run ALL, keep first error
  }
  if (hasError) throw firstError;
  return restart(context);                                     // only after every cleanup succeeded/ran
}
```
```ts
// exitHook SIGINT rule: exit ONLY when we are the sole listener (others may want to handle it)
if (type === 'SIGINT') {
  const listeners = process.listeners('SIGINT');
  if (Array.isArray(listeners) && listeners.length <= 1) { process.exit(exitCode); }
}
```
```ts
// watchFilesForRestart: single-flight + close-after-success retry semantics
const onWatchEvent = async (event, filePath, cwd) => {
  if (restarting || closePromise) return;    // one restart at a time; dead watcher stops triggering
  restarting = true;
  try {
    const restarted = await requestRestart({restartContext: {...restartContext, event, filePath}, ...});
    if (restarted) await close();            // close watcher ONLY on success — failed edits keep watching
    else if (restartManager.canRestart) logger.error('Restart server failed.');
  } catch (error) { logger.error(error); } finally { restarting = false; }
};
// chokidar created with ignoreInitial:true, ignorePermissionErrors:true; glob patterns expanded via tinyglobby
```

**Flow:** gracefulShutdown (dev/preview servers) registers SIGTERM (+128 POSIX code) and non-CI stdin-end handlers running all registered callbacks then `process.exit`; ref-counted teardown removes listeners only at zero. `requestRestart` is invoked by file watchers (config files + `dev.watchFiles type:'restart'`) or CLI 'r' shortcut; console clearing happens only when TTY and not DEBUG. tsconfig watch entries are added automatically when `aliasStrategy==='prefer-tsconfig'`.

**Invariant:** cleanup registry must be snapshot-and-swap so a cleanup registering new cleanups cannot recurse infinitely; first error wins and surfaces AFTER all cleanups attempt; restart success boolean gates watcher disposal everywhere.

**Probe:** `tests/restartHook.test.ts:4-27` pins all-cleanups-run-despite-throw, registry cleared after first invocation (`calls` unchanged across second request), and restart NOT called when a cleanup throws; `:29-39` pins unregister. Source comments pin SIGINT rule (exitHook.ts:22-25) and retryable-restart design (devServer.ts:211-212).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createRestartManager requestRestart watchFilesForRestart exitHook setupGracefulShutdown", limit: 10 });
```

## Verdict
Adopt swap-registry restart, first-error-wins aggregation, success-gated watcher disposal, and sole-listener SIGINT policy. Adapt signal set to host platform needs. Omit rsbuild's clearConsole ANSI specifics. Coverage caveat: direct unit tests exist for restartManager; watchers verified from source.
