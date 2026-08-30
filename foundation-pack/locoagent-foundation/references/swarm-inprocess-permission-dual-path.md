<!-- capsule-v2 -->
# In-process permission dual-path — how does a teammate's "ask" reach the leader without dropping into denial?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** when an in-process teammate hits a permission prompt, what decides between the leader's native dialog and the mailbox round-trip, and which state transitions must happen on every exit?

## createInProcessCanUseTool: bridge-first, mailbox-fallback
**Path/Symbol:** `src/utils/swarm/inProcessRunner.ts:createInProcessCanUseTool` (:128-451); bridge setters `src/utils/swarm/leaderPermissionBridge.ts:registerLeaderToolUseConfirmQueue` (:28-32), `getLeaderSetToolPermissionContext` (:48-50).
**Signature:** `(identity, abortController, onPermissionWaitMs?) => CanUseToolFn`.
**Data Shape:** allow/deny pass straight through; ONLY `behavior: 'ask'` enters the dual path. Every resolution reports elapsed wait via `onPermissionWaitMs` so the UI can subtract pause time from displayed elapsed.

### Decisive source
```ts
// Standard path: use ToolUseConfirm dialog with worker badge
if (setToolUseConfirmQueue) {
  return new Promise<PermissionDecision>(resolve => {
    let decisionMade = false
    // ... every resolver guards: if (decisionMade) return; decisionMade = true;
    //     removeEventListener('abort', onAbortListener); reportPermissionWait()
    async onAllow(updatedInput, permissionUpdates) {
      // ...
      // Preserve the leader's mode to prevent workers'
      // transformed 'acceptEdits' context from leaking back to the coordinator
      setToolPermissionContext(updatedContext, { preserveMode: true })
    }
```

**Flow:** forceDecision passthrough → classifier auto-approval AWAITED for bash (agents don't race it against user interaction like the main agent) → abort check before showing UI → bridge registered? enqueue `ToolUseConfirm` with `workerBadge: {name, color}` so the leader's dialog renders tool-specific UI with the teammate's identity : mailbox fallback: build request → `registerPermissionCallback` → send to leader's inbox → setInterval(500ms) poll of OWN mailbox for matching `request_id`, resolving via the callback.
**Invariant:** single-resolution guard (`decisionMade`) on ALL five exits (allow/reject/onUserInteraction-abort/signal-abort/recheckPermission) — double-resolve is the classic port bug; abort listeners are removed exactly once; recheckPermission re-runs full evaluation and can resolve allow mid-dialog when rules changed; worker permission-updates persist AND write back to leader context but never change the leader's mode.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'preserveMode: true' src/utils/swarm/inProcessRunner.ts` (:278-279); `grep -n 'decisionMade' src/utils/swarm/inProcessRunner.ts | head -3` (:200 etc.); `grep -n 'PERMISSION_POLL_INTERVAL_MS = 500' src/utils/swarm/inProcessRunner.ts` (:114).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createInProcessCanUseTool registerLeaderToolUseConfirmQueue getLeaderSetToolPermissionContext", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the module-setter bridge for letting non-React code drive React-owned dialogs, the ask-only dual path, and the one-guard-per-promise-exit pattern; adapt dialog plumbing; omit the bash-classifier feature flag if your stack lacks it.
