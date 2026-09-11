<!-- capsule-v2 -->
# Session-scoped runtime store — how do concurrent pi sessions share one server without sharing state?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** What is the cache key for experiment state, and what exactly does a session switch clear?

## sessions Map keyed cwd:sessionId — ensure-on-access, clear only on 'new'
**Path/Symbol:** `harness/server.ts` — `sessions` Map :626, `getSession(cwd, sessionId)` :628–636, dispatch entry :723 (`getSession(cwd, sessionId)`), x-session-id/x-cwd headers :1654–1656; CLI side `readSessionIdFromFile` :102–112 (writes `.pi/autoresearch/session-id` from extension `writeSessionId` index.ts :426–436).
**Signature:** key = `` `${cwd}:${sessionId}` `` when sessionId present else bare `cwd`; extension twin: `runtimeStore.ensure(sessionId)` over `Map<string, AutoresearchRuntime>` (`src/state/index.ts:50–71`).
**Data Shape:** SessionState `{ autoresearchMode, worktreeDir, state, startingCommit, lastRunChecks, lastRunDuration, experimentCompletedWaitingForLog, runningExperiment, lastRunSucceeded }`; reconstruction preserves ONLY `worktreeDir`.

### Decisive source
```ts
function getSession(cwd: string, sessionId?: string): SessionState {
  const key = sessionId ? `${cwd}:${sessionId}` : cwd;
  // ...
}
// reconstructStateFromJsonl — full reset except the worktree pointer:
const preservedWorktreeDir = session.worktreeDir;
session.state = createExperimentState();
/* ...every transient field nulled... */
if (preservedWorktreeDir) session.worktreeDir = preservedWorktreeDir;
```

**Flow:** every CLI/HTTP action carries `x-cwd` + optional `x-session-id`; two shells in one directory but different pi sessions get SEPARATE state (separate worktrees under `autoresearch/<id>`). Extension-side mirrors this with per-session runtime keyed by pi's sessionId (`getRuntime(ctx)`); `session_before_switch reason==='new'` clears UI + deletes the runtime entry; plain switches keep state but cancel resume timers and stop watchers. Reconstruction (watcher tick or action) rebuilds everything from JSONL while pinning the worktree pointer back afterward.
**Invariant:** the worktree pointer is the ONLY in-memory value allowed to survive a full state reset — losing it would orphan the isolated checkout mid-loop. Session-id absence degrades gracefully to cwd-keyed state (single-session CLIs). The file bridge (`.pi/autoresearch/session-id`) exists because the CLI runs OUTSIDE the extension process and must discover which session it serves.
**Probe:** direct tests `__tests__/unit/runtime-store.test.ts` ('Runtime Store Session Isolation') + `__tests__/integration/session-isolation.test.ts` (four describes incl. file isolation between sessions); anchor `grep -n 'getSession(cwd, sessionId)' harness/server.ts` → exactly :723; `grep -c preservedWorktreeDir harness/server.ts extensions/pi-autoresearch/src/lifecycle/handlers.ts` → 3 (server) + 4 (handlers) = 7 lines across both reconstructors.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "getSession sessions map x-session-id runtimeStore", limit: 10 });
```

## Verdict
Adopt composite-key isolation + preserve-only-worktree reconstruction verbatim; adapt the key material to your host's session identity; omit the disk session-file bridge when CLI and extension share a process. Direct tests cover both store isolation and cross-session file isolation.
