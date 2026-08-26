<!-- capsule-v2 -->
# Teammate idle notification hooks — how does a process-based teammate tell the leader it stopped?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** what hook, identity resolution, and await discipline deliver the idle notification reliably at session Stop?

## Stop-hook registration with teamAllowedPaths pre-application
**Path/Symbol:** `src/utils/swarm/teammateInit.ts:initializeTeammateHooks` (:28-129).
**Signature:** `(setAppState, sessionId, teamInfo: {teamName, agentId, agentName}) => void`.
**Data Shape:** hook options `{ timeout: 10000 }`; returns `true` ("Don't block the Stop").

### Decisive source
```ts
async (messages, _signal) => {
  // Mark this teammate as idle in the team config (fire and forget)
  void setMemberActive(teamName, agentName, false)
  // Send idle notification to the team leader using agent name (not UUID)
  // Must await to ensure the write completes before process shutdown
  const notification = createIdleNotification(agentName, {
    idleReason: 'available',
    summary: getLastPeerDmSummary(messages),
  })
  await writeToMailbox(leadAgentName, { from: agentName, text: jsonStringify(notification), ... })
  return true // Don't block the Stop
}
```

**Flow:** early in teammate startup: read team file → apply `teamAllowedPaths` as session-scoped allow rules (`//path/**` for absolute — note the DOUBLE slash prefix — vs `path/**` relative) via applyPermissionUpdate → resolve leader's NAME from members array (fall back to literal 'team-lead') → skip entirely if this IS the leader → register Stop hook: fire-and-forget isActive=false write + AWAITED mailbox idle-notification write (10s budget), then return true.
**Invariant:** mailbox writes must be awaited inside shutdown-path hooks (process may die after); active-flag updates must NOT be awaited (they'd delay stop for file I/O); notifications address the leader by NAME because mailboxes key on names, not UUIDs.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'Must await to ensure the write completes' src/utils/swarm/teammateInit.ts` (:108); `grep -n "startsWith('/')" src/utils/swarm/teammateInit.ts` (:53).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "initializeTeammateHooks createIdleNotification addFunctionHook", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt mixed await/fire-and-forget discipline in shutdown hooks by durability need; adapt rule grammar; omit allowed-paths application if your permission system differs.
