<!-- capsule-v2 -->
# Merged-base editing — Which constellation copy should a planner edit against?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** Before an agent applies structural edits mid-run, how does it obtain a base that contains both prior edits AND current execution truth?

## Edit base = synchronizer merge of the orchestrator copy
**Path/Symbol:** `galaxy/agents/constellation_agent_states.py:ContinueConstellationAgentState._get_merged_constellation` (:147-180); merge engine is pass-1's `merge_and_sync_constellation_states` (`galaxy/session/observers/constellation_sync_observer.py`, :384-451).
**Signature:** `async def _get_merged_constellation(self, agent: "ConstellationAgent", orchestrator_constellation) -> TaskConstellation`.
**Data Shape:** Input: the orchestrator-side constellation carried on the completion event; output: a merged copy whose structure includes agent edits and whose per-task states respect the advancement ladder PENDING(0) < WAITING_DEPENDENCY(1) < RUNNING(2) ≤ terminal(3). Fail-soft path returns the raw orchestrator copy when no synchronizer exists.

### Decisive source
```python
synchronizer = agent.orchestrator._modification_synchronizer
if not synchronizer:
    return orchestrator_constellation   # fail open to execution truth

merged_constellation = synchronizer.merge_and_sync_constellation_states(
    orchestrator_constellation=orchestrator_constellation)
agent.logger.info(
    f"🔄 Real-time merged constellation for editing. "
    f"Tasks before: {len(orchestrator_constellation.tasks)}, "
    f"Tasks after merge: {len(merged_constellation.tasks)}")
return merged_constellation
```

**Flow:** task completes → event delivers the orchestrator's live constellation → BEFORE editing, the consumer re-merges via the synchronizer so "task_2 editing sees task_1's modifications even if task_1 editing completed while task_2 was running" → merged copy becomes `before_constellation` for process_editing.
**Invariant:** an editor must never base edits on a stale private snapshot — the edit base must be re-derived at edit time from both copies; without a synchronizer the orchestrator copy wins (execution truth over planner memory), never vice versa.
**Probe:** direct source read of :147-180 via graph snippet + byte-parity read pattern; complements (does not duplicate) the `two-copy-dag-state-merge` capsule, which documents the merge ladder itself on the orchestrator-loop side — this capsule documents the consumer-side contract: WHEN the merge runs (per-editing-pass) and WHAT fails open. Direct test: covered indirectly by `tests/test_constellation_sync_observer.py:175-294` (pass-1 probe of the merge engine).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "ufo", function_name: "ufo.galaxy.agents.constellation_agent_states.ContinueConstellationAgentState._get_merged_constellation", direction: "outbound", depth: 1 });
```

## Verdict
Adopt the rule: re-merge immediately before every mutation pass, treating the executor's copy as ground truth and the planner's edits as structure to preserve. Adapt the merge implementation to your state model (UFO uses an advancement-priority ladder per task). Omit the logging/counters. If you have no concurrent editor, skip this entirely and edit the executor's copy directly.
