<!-- capsule-v2 -->
# JSONL file watcher — how does the UI track a file the server writes without an event bus?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** How is real-time UI achieved across processes, and what is the watcher lifecycle?

## fs.watchFile 500ms poll → reconstruct → updateWidget; close on switch/shutdown/off/clear
**Path/Symbol:** extension copy `extensions/pi-autoresearch/index.ts:startJsonlWatcher` :346–370 + reconstructor :372–420; lifecycle twin `src/lifecycle/handlers.ts:149–177` (mtime-guarded variant); runtime slot `jsonlWatcher: { close(): void } | null`.
**Signature:** `fs.watchFile(jsonlPath, { interval: 500 }, cb)`; handle stored on the per-session runtime so exactly one watcher exists.
**Data Shape:** watch target = `<workDir>/autoresearch.jsonl`; callback chain = full JSONL replay + widget refresh.

### Decisive source
```ts
if (runtime.jsonlWatcher) return;              // idempotent start — never double-watch
// ...
fs.watchFile(jsonlPath, { interval: 500 }, () => {
  reconstructStateFromJsonl(runtime, workDir);
  updateWidget(extCtx);
});
runtime.jsonlWatcher = { close() { fs.unwatchFile(jsonlPath); } };
```

**Flow:** session_start (after worktree detect + auto-activate when JSONL exists) starts the watcher; every tick that observes change re-reads the WHOLE file, rebuilds ExperimentState (preserving only worktreeDir), recomputes baseline, refreshes widget. This makes manual edits and external writers first-class: docs promise "Edit the file and the dashboard updates automatically". Teardown at session_before_switch / shutdown / `/autoresearch off` / `clear` — each path closes THEN nulls the handle before any new start can run.
**Invariant:** polling (not inotify) is deliberate: it works across network filesystems and containers where fs events are unreliable, and 500ms is imperceptible for benchmark cadence. The single-handle rule prevents duplicate widgets from stacked watchers. Extension-side reconstruction sets `confidence = null` ("computed on server side", :415) — display falls back to server-persisted per-row confidence values instead of recomputing with divergent logic.
**Probe:** direct test `__tests__/unit/jsonl.test.ts:274–283` ('createSessionRuntime initializes jsonlWatcher to null'); anchors: `grep -n 'watchFile' extensions/pi-autoresearch/index.ts extensions/pi-autoresearch/src/lifecycle/handlers.ts harness/cli.ts | wc -l` → 3 (jsonl watcher ×2 + CLI --logs follower); `grep -c 'unwatchFile' extensions/pi-autoresearch/index.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "startJsonlWatcher watchFile unwatchFile reconstructStateFromJsonl", limit: 10 });
```

## Verdict
Adopt poll-based whole-file reconstruction for cross-process UI truth; adapt interval/handle type to host; omit the mtime-guard twin detail (handlers.ts checks curr!==prev.mtime) unless you need tick dedup. Coverage caveat: watcher lifecycle itself untested — source-pinned via jsonl.test's runtime assertions.
