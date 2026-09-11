<!-- capsule-v2 -->
# Reservation conflict gate — how are file edits blocked across agents without a VCS?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How do reservations work end-to-end: claim, conflict detection, enforcement, release?

## Glob-lite patterns on registrations + tool_call interception
**Path/Symbol:** `lib/paths.ts:pathMatchesReservation` (:36-41), `store/agents.ts:getConflictsWithOtherAgents` (:218-242), `handlers/coordination/reservations.ts:executeReserve` (:6-43) / `executeRelease` (:45-85), `extension/reservation.ts:handleReservationEnforcement` (:10-37).
**Signature:** `pathMatchesReservation(filePath, pattern): boolean`; enforcement returns `{block:true, reason} | undefined`.
**Data Shape:** `FileReservation { pattern, reason?, since }` persisted INSIDE each agent's registration JSON (no separate store).

### Decisive source
```ts
export function pathMatchesReservation(filePath: string, pattern: string): boolean {
  if (pattern.endsWith('/')) {
    return filePath.startsWith(pattern) || filePath + '/' === pattern;  // dir = prefix OR exact-dir
  }
  return filePath === pattern;                                          // file = exact only
}
```
```ts
// extension/reservation.ts — the ONLY blocking point
if (!['edit', 'write'].includes(event.toolName)) return;
const conflicts = store.getConflictsWithOtherAgents(filePath, state, dirs);
if (conflicts.length === 0) return;
return { block: true, reason: lines.join('\n') };  // names holder + branch + contact command
```

**Flow:** reserve checks conflicts for paths[0] only before accepting ANY of the batch → pushes onto own state → registration rewrite persists them. Enforcement is a tool_call hook: edit/write with a path matching ANOTHER live agent's pattern gets blocked with a message that includes the coordinating send command. Release supports all (`paths === true`) or per-pattern with notFound reporting.
**Invariant:** Conflict detection is SYMMETRIC but advisory-by-tool-surface: only edit/write are intercepted (bash writes pass), and only OTHER agents' reservations block you — your own never do. Dir patterns are prefix-based WITHOUT trailing-content normalization, so `src/auth/` matches `src/auth/x.ts` but not `src/auth.ts`. First-conflict-wins in the block reason.
**Probe:** direct tests `tests/swarm/session-shutdown-cleanup.test.ts::should clean up file reservations when agent leaves` (:375); `grep -c "endsWith('/')" lib/paths.ts` (=1); `grep -n "'edit', 'write'" extension/reservation.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "pathMatchesReservation getConflictsWithOtherAgents handleReservationEnforcement executeReserve", limit: 6 });
```

## Verdict
Adopt registration-embedded reservations + two-glob grammar + tool-hook enforcement naming the holder; adapt to your tool names (add MultiEdit-style tools to the intercept list); omit bash-write coverage honestly if unenforceable.
