<!-- capsule-v2 -->
# Shutdown ordering — when a leader dies without cleanup, what must be killed before directories are deleted?

**Source:** locoagent (Claude Code CLI fork, MIT), rev `c01bb3f`; Codebase Memory `locoagent`. **Question:** in ungraceful leader exit (SIGINT/SIGTERM), why does pane-killing precede directory deletion and how are orphan teams tracked?

## cleanupSessionTeams: panes first, dirs second, session-Set tracking
**Path/Symbol:** `src/utils/swarm/teamHelpers.ts:registerTeamForSessionCleanup` (:560-562), `cleanupSessionTeams` (:576-590), `killOrphanedTeammatePanes` (:598-634), `destroyWorktree` (:492-551); registration site `src/entrypoints/init.ts:196-200`.
**Signature:** `cleanupSessionTeams(): Promise<void>`.
**Data Shape:** backing Set lives in bootstrap/state.ts so `resetStateForTests()` clears it ("avoids the PR #17615 cross-shard leak class").

### Decisive source
```ts
// Kill panes first — on SIGINT the teammate processes are still running;
// deleting directories alone would orphan them in open tmux/iTerm2 panes.
// (TeamDeleteTool's path doesn't need this — by then teammates have
// gracefully exited and useInboxPoller has already closed their panes.)
await Promise.allSettled(teams.map(name => killOrphanedTeammatePanes(name)))
await Promise.allSettled(teams.map(name => cleanupTeamDirectories(name)))
```
destroyWorktree ladder: read worktree `.git` file → parse `gitdir:` line → derive main repo path (two levels up from `.git/worktrees/name`) → `git worktree remove --force` from the MAIN repo cwd → treat "not a working tree" stderr as already-removed success → fallback `rm -rf`.

**Flow:** TeamCreate registers the team name right after initial writeTeamFile; explicit TeamDelete UNregisters (already cleaned — don't double-clean at shutdown) → on graceful shutdown, init's registerCleanup callback imports and runs cleanupSessionTeams → for each remaining team: kill pane-backed members via their STORED backendType (`getBackendByType(m.backendType).killPane(paneId, useExternalSession)` where useExternalSession = NOT insideTmux) with dynamic imports "to avoid adding registry/detection to this module's static dep graph", THEN delete worktrees/team dir/tasks dir.
**Invariant:** live processes before dead data — reverse order strands visible panes running dead sessions; per-member stored backendType (not global detection) decides HOW to kill because members may span backends; every step is best-effort under Promise.allSettled.
**Probe:** coverage caveat (no direct tests). Deterministic probes: `grep -n 'Kill panes first' src/utils/swarm/teamHelpers.ts` (:584-586); `grep -n 'cross-shard leak' src/utils/swarm/teamHelpers.ts` (:558).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "cleanupSessionTeams killOrphanedTeammatePanes destroyWorktree unregisterTeamForSessionCleanup", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt process-before-data teardown ordering, session-scoped created-resource Sets with explicit deregistration on manual deletes, and git-first worktree destruction with rm fallback; adapt paths; omit WSL-specific instructions.
