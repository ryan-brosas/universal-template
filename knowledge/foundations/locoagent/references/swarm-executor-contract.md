<!-- capsule-v2 -->
# Teammate executor contract — one interface for pane processes and in-process agents?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what single contract lets a leader spawn/message/terminate teammates identically whether they are tmux panes or AsyncLocalStorage-isolated in-process loops?

## Two-level abstraction: PaneBackend ops vs TeammateExecutor lifecycle
**Path/Symbol:** `src/utils/swarm/backends/types.ts:PaneBackend` (:39-168), `TeammateExecutor` (:279-300), `TeammateSpawnConfig` (:205-225), `TeammateSpawnResult` (:230-254), `isPaneBackend` (:309-311).
**Signature:** `spawn(config: TeammateSpawnConfig): Promise<TeammateSpawnResult>`; `sendMessage(agentId: string, message: TeammateMessage)`; `terminate(agentId, reason?)`; `kill(agentId)`; `isActive(agentId)`.
**Data Shape:** `TeammateSpawnResult` carries EITHER `{ abortController?, taskId? }` (in-process) OR `{ paneId? }` (pane-based); agentId is always the logical `agentName@teamName`, taskId only indexes AppState.

### Decisive source
```ts
/**
 * Result from spawning a teammate.
 */
export type TeammateSpawnResult = {
  success: boolean
  /** Unique agent ID (format: agentName@teamName) */
  agentId: string
  error?: string
  /**
   * Abort controller for lifecycle management (in-process only).
   * Leader uses this to cancel/kill the teammate.
   * For pane-based teammates, use kill() method instead.
   */
  abortController?: AbortController
  /** Task ID in AppState.tasks (in-process only). ... agentId is the logical
   *  identifier; taskId is for AppState indexing. */
  taskId?: string
  /** Pane ID (pane-based only) */
  paneId?: PaneId
}
```

**Flow:** callers take `TeammateExecutor` from `getTeammateExecutor(preferInProcess)` and never branch on backend type → graceful terminate = send shutdown REQUEST (the teammate's model decides via approve/reject tools); force kill = immediate AbortController.abort() or killPane → identity fields (`TeammateIdentity`) are deliberately a SUBSET shared with TeammateContext to avoid circular deps; `allowPermissionPrompts` defaults FALSE ("when false, unlisted tools are auto-denied") — deny-by-default posture lives in the contract itself.
**Invariant:** dual identity (logical agentId vs UI taskId) must never be conflated; termination comes in exactly two strengths with different mechanisms per backend; permission surface narrows by default.
**Probe:** coverage caveat (no direct tests). Deterministic probe: `grep -n 'agentId is the logical identifier' src/utils/swarm/backends/types.ts` (:248).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "TeammateExecutor PaneBackend TeammateSpawnConfig CreatePaneResult", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-level split (low-level pane ops vs high-level lifecycle) and the union result shape that makes execution mode visible at the type level; adapt tool names and color types; omit the AgentColorName coupling if you have no swarm UI.
