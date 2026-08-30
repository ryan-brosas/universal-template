<!-- capsule-v2 -->
# Leader-by-absent-identity — how do you tell the team lead from a teammate without a role flag?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what single signal distinguishes leader from teammate across the swarm code, and where does each variant live?

## Three instances of one pattern: absence of agent identity ⇒ leader
**Path/Symbol:** `src/utils/swarm/permissionSync.ts:isTeamLeader` (:581-591); `src/utils/swarm/reconnection.ts:computeInitialTeamContext` (:51 `const isLeader = !agentId`); `src/utils/swarm/teammateInit.ts` (:86-91 `if (agentId === leadAgentId) skip idle-notification hook`).
**Signature:** `isTeamLeader(teamName?): boolean` — "Team leaders don't have an agent ID set, or their ID is 'team-lead'".
**Data Shape:** env/CLI-provided identity (`CLAUDE_CODE_AGENT_ID` etc. via getAgentId/getTeamName); leader spawns carry NO --agent-id flag (PaneBackendExecutor builds teammate args with --agent-id only for teammates).

### Decisive source
```ts
// permissionSync.ts:
export function isTeamLeader(teamName?: string): boolean {
  const team = teamName || getTeamName()
  if (!team) return false
  // Team leaders don't have an agent ID set, or their ID is 'team-lead'
  const agentId = getAgentId()
  return !agentId || agentId === 'team-lead'
}
```

**Flow:** spawn side: only teammates receive identity flags/env → any process lacking them IS the leader → permissionSync treats absent-ID agents as resolution authorities; reconnection computes AppState.teamContext.isLeader synchronously pre-render; teammateInit registers the Stop-hook idle notification ONLY for non-leaders (the leader's own stop must not message itself); mailbox writes target the leader BY NAME resolved from team file members (getLeaderName falls back to literal 'team-lead').
**Invariant:** leadership is derived, never stored as a boolean on disk — one source of truth (identity presence) across three modules; adding a stored isLeader field would fork the truth and desynchronize spawn-time vs runtime views.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n "ID is 'team-lead'" src/utils/swarm/permissionSync.ts` (:587); `grep -n 'const isLeader = !agentId' src/utils/swarm/reconnection.ts` (:51).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isTeamLeader isSwarmWorker computeInitialTeamContext", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt derived-role detection from spawn-parameter presence; adapt the sentinel string; omit the 'team-lead' alias if your IDs are always present.
