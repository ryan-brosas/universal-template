<!-- capsule-v2 -->
# team-run-wait-ladder — how does a parent agent session wait for async teammate runs and feed outcomes back as its own next turn?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How should a session track in-flight teammate runs, block on their terminal events without busy-waiting or losing updates, decide when auto-continue is legal, and synthesize the continuation prompt?

## Active-set + pending-queue with parked waiters; finishReason allowlist; mode-formatted continuation
**Path/Symbol:** `sdk/packages/core/src/session/team/team-session-coordinator.ts` (`trackTeamRunState` :14-52, `hasPendingTeamRunWork` :163-168, `shouldAutoContinueTeamRuns` :170-185, `notifyTeamRunWaiters` :187-190, `waitForTeamRunUpdates` :192-207, `buildTeamRunContinuationPrompt` :209-230).
**Signature:** `waitForTeamRunUpdates(session): Promise<TeamRunUpdate[]>`; `shouldAutoContinueTeamRuns(session, finishReason): boolean`; `buildTeamRunContinuationPrompt(session, updates): string`.
**Data Shape:** ActiveSession carries `activeTeamRunIds: Set`, `pendingTeamRunUpdates: TeamRunUpdate[]`, `teamRunWaiters: Array<() => void>`, `aborting: boolean`; TeamRunUpdate{runId, agentId, taskId?, status: completed|failed|cancelled|interrupted, error?, iterations?}.

### Decisive source
```ts
// Terminal events move a run from active to pending and wake the waiter:
case "run_completed": case "run_failed": case "run_cancelled": case "run_interrupted": {
	// error extraction: failed => run.error; cancelled/interrupted => run.error ?? event.reason
	session.activeTeamRunIds.delete(event.run.id);
	session.pendingTeamRunUpdates.push({runId, agentId, taskId, status, error, iterations});
	notifyTeamRunWaiters(session);            // splice(0) + resolve each — no lost wakeups
}

// The wait ladder — abort beats pending, pending drains atomically, idle exits:
export async function waitForTeamRunUpdates(session) {
	while (true) {
		if (session.aborting) return [];
		if (session.pendingTeamRunUpdates.length > 0) { const updates = [...session.pendingTeamRunUpdates]; session.pendingTeamRunUpdates.length = 0; return updates; }
		if (session.activeTeamRunIds.size === 0) return [];
		await new Promise<void>((resolve) => { session.teamRunWaiters.push(resolve); });
	}
}

// Auto-continue is a triple gate:
if (session.aborting) return false;
const canAutoContinue = finishReason === "completed" || finishReason === "max_iterations";
return session.config.enableAgentTeams === true && hasPendingTeamRunWork(session);   // after canAutoContinue check
```

**Flow:** run queued/started ⇒ id added | run reaches terminal state ⇒ id removed, update pushed, waiters resolved | parent turn ends ⇒ shouldAutoContinueTeamRuns gates (not aborting ∧ finishReason ∈ {completed, max_iterations} ∧ teams enabled ∧ work outstanding) ⇒ waitForTeamRunUpdates parks until updates exist ⇒ buildTeamRunContinuationPrompt renders `- runId (agentId) -> status [task=…] [iterations=…] [error=…]` plus remaining-count instruction, wrapped by formatModePrompt→formatUserInputBlock honoring plan/yolo/act mode.
**Invariant:** Updates are never dropped (queue drains only via snapshot-copy) and never delivered twice (single drain point); waiting is event-driven through parked resolvers — one wakeup per terminal event batch; abort always wins immediately with empty results; auto-continue cannot fire from failed/aborted turns. Coverage caveat: this file has NO colocated direct test; nearest behavioral pins live in multi-agent.lifecycle.test.ts ("marks an active queued run as cancelled when teammate shutdown aborts it", "queues steer message notification when recipient is running") and the importer surface session/team/index.ts.
**Probe:** `grep -cF 'session.teamRunWaiters.push(resolve);' …team-session-coordinator.ts` → 1; `grep -cF 'finishReason === "completed" || finishReason === "max_iterations"' …` → 1; `grep -cF 'notifyTeamRunWaiters(session);' …` → 1; corrected fixed-string probe `grep -cF 'if (session.aborting) return [];' …` → 1. All executed pre-write, exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.session.team.team-session-coordinator.waitForTeamRunUpdates" });
// observed: Function lines 192-207 verbatim; callers_total 1 (session/team/index.ts barrel)
```

## Verdict
Adopt the active-set/pending-queue/parked-waiter triple and its drain discipline, the finishReason allowlist plus config+abort gates for auto-continue, and prompt synthesis that states remaining-work counts explicitly. Adapt TeamRunUpdate fields and prompt copy to host vocabulary. Omit AgentTeamsRuntime scheduling internals (busy-suppression, retry backoff, mailbox prepend) — queued as a separate target. Runner-BLOCKED here; probes green.
