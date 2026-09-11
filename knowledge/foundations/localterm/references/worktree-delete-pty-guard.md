<!-- capsule-v2 -->
# Worktree delete PTY guard — how do you stop a directory removal from pulling the ground out from under a live shell, including a parked one?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How does a daemon refuse `git worktree remove` while any PTY occupies the tree (attached OR dormant-parked), and how does the client learn that before offering the button?

## One occupancy predicate, three consumers
**Path/Symbol:** `packages/server/src/index.ts:DELETE /git/worktrees` (:1773–1801), GET route injection (:1637–1650), sweep injection (:1725–1742); occupancy source `packages/server/src/session-manager.ts:SessionManager.sessionsInPath` (:417–424); service-level main-tree guard `packages/server/src/git-worktrees.ts:removeGitWorktree` (:380–400).
**Signature:** route guard reads `registry.sessionsInPath(targetPath).length > 0` → 409 `{error:"active_pty", message}`; service `removeGitWorktree(cwd, targetPath): Promise<void>` throws `WorktreeError("can't remove the main worktree")`.
**Data Shape:** List rows carry `activeSessionCount: number ≥ 0` — the SAME signal the delete route reads — so the client hides the trash action instead of offering a delete the server would 409.

### Decisive source
```ts
// A live shell sitting in the worktree (attached, dormant in the
// no-clients grace window, or running an automation) blocks removal —
// `git worktree remove` would pull the directory out from under the PTY.
const sessionsOnWorktree = registry.sessionsInPath(targetPath);
if (sessionsOnWorktree.length > 0) {
  const count = sessionsOnWorktree.length;
  return context.json(
    { error: "active_pty",
      message: `${count} shell${count === 1 ? "" : "s"} still open in this worktree — close ${count === 1 ? "it" : "them"} first` },
    HTTP_STATUS_CONFLICT,
  );
}
```
The containment matcher:
```ts
sessionsInPath(targetPath: string): SessionListItem[] {
  const resolvedTarget = path.resolve(targetPath);
  const prefix = `${resolvedTarget}${path.sep}`;
  return this.list().filter((session) => {
    const cwd = path.resolve(session.cwd);
    return cwd === resolvedTarget || cwd.startsWith(prefix);
  });
}
```

**Flow:** DELETE resolves the query path (relative anchored to cwd; absolute passes through — no traversal check because the daemon already grants unrestricted shells) → occupancy check FIRST (in-memory) → 409 with a count-aware human message if occupied → service call re-guards the MAIN worktree via realpath comparison (git would also refuse, but the explicit check gives a clear message before spawning git) → success `{ok:true}`. The parked-shell case is covered for free: a detached tab's PTY stays in the registry through the no-clients grace window, and `lastEmittedCwd` is seeded to the spawn cwd at construction — before any OSC7 arrives — so occupancy is visible the instant the session frame lands.
**Invariant:** Occupancy is decided by exact-or-`sep`-prefix containment of RESOLVED paths, so shells sitting in subdirectories also block. The list payload and the delete guard read one source of truth (`sessionsInPath`), making UI affordance and server enforcement unable to drift.
**Probe:** `packages/server/tests/worktree-delete-pty-guard.test.ts` (full createServer integration) — attached PTY ⇒ 409 active_pty :125–138; parked after WS close ⇒ still 409 :139–145; kill ⇒ 200 and directory gone :147–157; unoccupied remove 200 :167–172; `activeSessionCount` per row tracks attach/park/kill :174–216 (opens the shell at the REALPATH because git prints symlink-resolved paths). Executed this pass: 3/3 green.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "sessionsInPath registry active session worktree", limit: 10 });
```
Executed live pre-write: rank#1 `SessionManager.sessionsInPath` session-manager.ts :417–424; `get_code_snippet` returned source byte-equal to disk; client hook side ranked `useWorktreeActions` apps/terminal/src/hooks/use-worktree-actions.ts :46–191.

## Verdict
Adopt: one occupancy predicate injected into every destructive path (delete route, sweep busy-check, list payload), conflict-as-409-with-actionable-message, realpath-normalized main-tree refusal; adapt the "what counts as busy" definition to your process model; omit the subdirectory prefix match only if your sessions can never cd deeper. Trap: checking occupancy only for ATTACHED clients — a parked PTY in its grace window is still a live process whose cwd vanishes under it.
