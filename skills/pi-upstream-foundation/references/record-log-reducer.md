<!-- capsule-v2 -->
# Record-log reducer — how does a restart rebuild "what was this lane doing?" from raw records without guessing?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c`; Codebase Memory `pi-upstream`. **Question:** A porter recovers by re-running the agent loop over the last N entries — what does pi compute instead, and which corruption shapes must be detected first?

## validateRecordLog + reduceLaneState: pure validation then deterministic derivation
**Path/Symbol:** `packages/agent/src/harness/reducer.ts:312-390` (`validateRecordLog`), `:506-667` (`reduceLaneState`), helpers `:400-505` (`deriveEffectiveConfiguration`, `deriveNewestOwn`, `deriveToolBatch`).
**Signature:** `validateRecordLog(input: RecordLogSlice): void` (throws `RecordLogCorruption`); `reduceLaneState(input: LaneReductionInput): LaneReductionResult` — both PURE: no session reads, no mutation of inputs (test-pinned).
**Data Shape:** Output `laneState.operation` carries the full suspension picture: `{id, kind, intent, aborting, step (newest attempt whose resultEntryId is still missing), toolBatch, missingInitialMessages, pendingSteer, pendingFollowUp, pendingWrites, deferred, overflowRecoveryUsed, newestOwn, targets}` plus lane-level `pendingNextRun` and a separate `terminalFailure` verdict.

### Decisive source
```ts
export function validateRecordLog(input: RecordLogSlice): void {
	if (input.openOperations.length > 1) {
		corrupt("multiple_open_operations", `Lane ${input.lane} has at least two open operations`);
	}
...
	case "queue_cancelled": {
		const enqueue = queueEnqueues.get(record.entryId);
		if (
			!enqueue ||
			enqueue.seq >= record.seq ||
			enqueue.runId !== record.runId ||
			entriesById.has(record.entryId)
		) {
			corrupt("invalid_queue_cancellation", `Queue cancellation ${record.id} has no pending matching enqueue`);
		}
```

**Flow:** validate first — ≤1 open op; every runId-bearing record references a known operation; nothing follows its operation's finish; queue items never enqueued after abort (except `nextRun`, which survives abort by design); cancellations must match a strictly-later pending enqueue whose target entry doesn't exist; attempt sequences monotone; result entries type-match intents (run→initialMessages present, compaction→compaction entry, navigation→branch_summary entry). Then derive — effective configuration folds model/thinking/tools changes in seq order over defaults; abort kills steer+followUp queues but preserves pendingWrites and nextRun input; an assistant message with `stopReason:"error"` that was produced by the current step or a deferred fetch becomes `terminalFailure` (an error-shaped *deferred write* deliberately does NOT count — :1060 test). Overflow guard: `overflowRecoveryUsed` only when a compaction attempt for overflow happened AFTER the newest consumed conversational input (:582-593), so stale overflow history can't suppress future auto-compaction.
**Invariant:** Recovery state is a REDUCED FUNCTION of validated records + entries, never re-derived by replaying the loop — so recovery semantics are deterministic, unit-testable, and identical between crash-restart and live resumption. Corruption taxonomy is explicit and exhaustive (unknown_operation, record_after_finish, queue_after_abort, invalid_queue_cancellation, invalid_deferred_handle, multiple_open_operations…); anything not enumerated passes.
**Probe:** `packages/agent/test/harness/reducer.test.ts` — 16 direct tests incl. "does not mutate its bounded recovery inputs" :447, "kills steer and follow-up queues on abort while preserving writes and next-run input" :808, "closes the newest attempt only when its provisioned result exists" :858, "does not classify an error-shaped deferred write as terminal failure" :1060, "resets the overflow guard only after newer conversational input is consumed" :1097.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "reduceLaneState validateRecordLog corruption recovery", limit: 10, fields: ["signature", "name", "file"] });
```
(Resolves both functions at `reducer.ts:312-390` / `:506-667` ranks #1-#2.)

## Verdict
Adopt validate-then-derive as two pure functions with an explicit corruption taxonomy, abort semantics that preserve writes/nextRun while killing steer/followUp, terminal-failure classification requiring producer attribution, and the post-input reset rule for overflow recovery. Adapt record vocabulary and corruption codes to your operation set. Omit queue machinery if your host has no cross-run queues. Coverage: 16 direct unit tests at this pin; strongest-tested seam in this foundation.
