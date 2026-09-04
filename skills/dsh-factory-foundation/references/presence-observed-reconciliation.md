<!-- capsule-v2 -->
# Presence projection + observed-session reconciliation — how do live Sessions become durable work and settle honestly when they die?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I project live agent sessions into shared state (heartbeat presence) and reconcile observed sessions' lifecycle without inventing outcomes?

## publishPresence / observe / reconcileObservedState
**Path/Symbol:** `packages/domain/src/index.ts` (`schedulePresence`, `publishPresence`, `reconcileObservedState`, `observe`) (:1200–1294).
**Signature:** `private async publishPresence(): Promise<void>`; `replaceAgentObservations(processId, observations)` store API; `readAgentObservations(freshAfter)` prunes expired rows on read.
**Data Shape:** `FactoryAgentObservation { processId, agentId, sessionId, status, taskId?, runId?, cwd?, preset?, provider?, model?, title?, origin?: 'subagent', delegationDepth?, heartbeatAt }` — zod `.strict()` parsed as UNTRUSTED cross-process input (`parseFactoryAgentObservation`). Presence TTL default 15s; heartbeat 3s.

### Decisive source
```ts
} else if (agent.status === 'running' && run.status !== 'running') {
    run.status = 'running'; ...
}
// in the same loop, agent === undefined branch:
const failure = 'Observed Session ended before factory_finish'
run.status = 'failed'; run.failure = failure; ...
task.status = 'failed'; task.failure = failure; ...
delete task.activeRunId
```
plus the inbox auto-sink: after publishing, unassigned agents with a real user message are adopted via `adoptSessions` into the workspace's `Emerging work` inbox flow (status waiting).

**Flow:** events (`agent/created|status|disposed`, session titles, store commits) + heartbeat timer → single-flight `schedulePresence` (with `publishAgain` coalescing) → replace THIS process's presence rows wholesale → `reconcileObservedState`: canonicalize inbox flow titles, then per observed-origin run — live agent running→mark running; live agent gone→fail with "Observed Session ended before factory_finish" → auto-adopt still-unassigned messaging sessions into the inbox.
**Invariant:** A dead observed Session is a FAILED run, never a silent drop or invented success; each process owns only its own presence rows (owner-mismatch throws); presence reads double as expiry sweeps. The projection is strictly additive — assignments come from durable runs (`projectAgentAssignments`), not from guessing.
**Probe:** `packages/domain/tests/domain.spec.ts` "projects observed Session start and abrupt disappearance onto the task lifecycle" (agent/disposed → run+task failed with that exact failure string) and "automatically sinks a published live Agent without a browser mutation". Deterministic from repo root: `grep -c 'Observed Session ended before factory_finish' packages/domain/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "FactoryAgentObservation", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt process-owned heartbeat presence rows + honest abrupt-death settlement + inbox auto-sink of live sessions. Adapt event names to host agent lifecycle. Omit subagent/delegation-depth metadata fields if host lacks delegation.
