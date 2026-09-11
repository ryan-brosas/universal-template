<!-- capsule-v2 -->
# watchFiles groups + publicDir watcher — why do dev watchFiles and server publicDir get separate watcher lifecycles?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the two-group setup, event filtering, and close aggregation.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/watchFiles.ts` — DEFAULT_WATCH_FILE_EVENTS 13, `setupWatchFiles` 25–43 (gate 30–33), `watchDevFiles` 45–66 (per-entry watchers array), `watchServerFiles` 68–80+ (publicDir .watch flags).
**Signature:** `setupWatchFiles({root, config, buildManager?}): Promise<{close(): Promise<void>} | undefined>`.
**Data Shape:** dev.watchFiles: Array<{paths, type?, events?, options?}>; server.publicDir: Array{name, watch?, copyOnBuild?}.

### Decisive source
```ts
const { hmr, liveReload } = config.dev;
if ((!hmr && !liveReload) || !buildManager) return;   // no consumer → no watchers at all
...
return { async close() { await Promise.all([closeDevFilesWatcher?.(), serverFilesWatcher?.close()]); } };
```
```ts
for (const { paths, events, options, type } of castArray(watchFiles)) {
  const watchOptions = prepareWatchOptions(paths, options, type, events);   // per-group chokidar opts + event filter
  const watcher = await startWatchFiles(watchOptions, buildManager, root);
```

**Flow:** dev watchFiles entries each become their OWN chokidar instance so per-group ignore globs and event subsets don't interfere; matched add/change/unlink events trigger buildManager rebuilds (the same recompile path as bundler-internal changes). publicDir watching is opt-in per dir and exists because copied static files bypass the module graph — the bundler can't see them.
**Invariant:** (1) the hmr/liveReload gate must precede any fs.watch or CI runs leak open handles that keep processes alive; (2) close() aggregates BOTH groups in one Promise.all or restart cycles accumulate watchers; (3) castArray normalizes single-object configs.
**Probe:** e2e `cases/config/watch-files*` / server public-dir cases pin rebuild-on-copy behavior; unit coverage absent (coverage caveat: source read).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "setupWatchFiles watchDevFiles watchServerFiles startWatchFiles", limit: 8 });
```

## Verdict
Adopt grouped watcher instantiation with aggregate close and the no-consumer early return. Adapt chokidar options to host. Omit copyOnBuild logic (covered by server plugin surface).
