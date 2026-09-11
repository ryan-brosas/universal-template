<!-- capsule-v2 -->
# Teammate spawn/terminate lifecycle — what does spawning an in-process teammate deliberately NOT inherit, and how do graceful vs force termination differ?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** which parent resources must an in-process teammate share, which must be stripped, and what exactly happens on terminate() vs kill()?

## Independent AbortController + messages-strip + request-based termination
**Path/Symbol:** `src/utils/swarm/spawnInProcess.ts:spawnInProcessTeammate` (:104-216, abort comment :120-122), `startInProcessTeammate` (:1544-1552); `src/utils/swarm/backends/InProcessBackend.ts:spawn` (:72-143), `terminate` (:192-253), `kill` (:261-290).
**Signature:** `spawnInProcessTeammate(config, context): Promise<InProcessSpawnOutput>`; `terminate(agentId, reason?): Promise<boolean>`.
**Data Shape:** fire-and-forget start with closure slimming: "Extract agentId before the closure so the catch handler doesn't retain the full config object (including toolUseContext) while the promise is pending - which can be hours for a long-running teammate."

### Decisive source
```ts
// Create independent AbortController for this teammate
// Teammates should not be aborted when the leader's query is interrupted
const abortController = createAbortController()
```
```ts
// Strip messages: the teammate never reads toolUseContext.messages
// (runAgent overrides it via createSubagentContext). Passing the
// parent's conversation would pin it for the teammate's lifetime.
toolUseContext: { ...this.context, messages: [] },
```
Terminate dedup (:216-224): "Don't send another shutdown request if one is already pending" → `if (task.shutdownRequested) return true`.

**Flow:** spawn creates identity/context/task state (`permissionMode: planModeRequired ? 'plan' : 'default'`, empty pendingUserMessages/messages arrays so UI works immediately) → registers cleanup that ABORTS on leader exit → registerTask → backend starts runner detached. Terminate = mailbox `shutdown_request` message + `requestTeammateShutdown` flag (model approves/rejects via tools); Kill = direct AbortController.abort() inside a status-guarded updater ('killed', bookend protocol per swarm-terminal-state-guards). isActive = status==='running' AND signal not aborted.
**Invariant:** teammates survive leader Escape (independent controller) but not leader process exit (cleanup registration); parent conversation must NEVER be pinned into a teammate context (hours-long memory retention); graceful termination is idempotent via the shutdownRequested flag; spinner verbs/past-tense verbs are sampled at spawn for UI personality only.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'not be aborted when the leader' src/utils/swarm/spawnInProcess.ts` (:121); `grep -n 'would pin it for the teammate' src/utils/swarm/backends/InProcessBackend.ts` (:121).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "spawnInProcessTeammate startInProcessTeammate createTeammateContext requestTeammateShutdown", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt independent abort scopes for supervised-but-long-lived agents plus explicit stripping of parent conversation handles; adapt task-state shape; omit plan-mode plumbing if unused.
