<!-- capsule-v2 -->
# Run resume & thread time-travel — how does a checkpointed run continue with its identity, and how do you branch instead of rewriting?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you resume the SAME run (same ids, budgets, todos) from a checkpoint — and how do you roll back to an earlier turn as a NEW branch without mutating history?

## Restore context + budget + identity quintet, then re-enter agent.run() on the SAME instance
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/resume.py` — `resume()` (:19-90), `resume_thread()` (:93-111), `rollback()` (:114-152). Exposed on the Agent facade: `backend/python/app/agent_loop_lib/agent/__init__.py:1012` (`return await agent_resume.resume(self, checkpoint_id, hil_responses=hil_responses)`).
**Signature:** `async def resume(agent, checkpoint_id, hil_responses=None) -> AgentResult`; `async def resume_thread(agent, thread_id, hil_responses=None)`; `async def rollback(agent, thread_id, turn_index, hil_responses=None)`. All take the owning `agent` first (observability.py convention) and mutate ITS state.
**Data Shape:** Uses checkpoint fields: `messages`, `goal`, `turn_index`, `budget_snapshot`, identity quintet (`run_id/agent_id/parent_run_id/trace_id/spawn_depth`), `started_at`, `todos`, `extensions`; rollback adds `metadata` passthrough. `thread_id == run_id` by design — no separate conversation identifier exists because run_id survives pause/resume unchanged.

### Decisive source
```python
    # resume(): re-enter run() on the calling instance, not a throwaway copy
    agent.seed_context(context)
    if runtime.budget is not None:
        await runtime.budget.restore(checkpoint.budget_snapshot)
    agent._run_ctx = agent._run_ctx.model_copy(update={
        "run_id": checkpoint.run_id, "agent_id": checkpoint.agent_id,
        "parent_run_id": checkpoint.parent_run_id,
        "trace_id": checkpoint.trace_id, "spawn_depth": checkpoint.spawn_depth,
    })
    return await agent.run(
        checkpoint.goal,
        _resume_turn_index=checkpoint.turn_index + 1,   # NEXT turn, never re-issue
        _resume_started_at=checkpoint.started_at,
        _resume_todos=list(checkpoint.todos),
        _resume_extensions=dict(checkpoint.extensions),
        _skip_start=True,
    )
```

**Flow (resume):** guard no-store → `load(checkpoint_id)` → fresh ContextManager replaying messages (+ HIL answer injection per the dual-id capsule) → `seed_context` → restore budget counters → overwrite `_run_ctx` with the checkpoint's identity quintet → `run()` with private `_resume_*` kwargs (RunScope rebuilds todos/extensions and skips start). **(rollback):** `history(thread_id)` → filter `cp.turn_index <= target` → pick max-turn_index candidate → `model_copy` a branch checkpoint with NEW uuids for checkpoint_id+run_id but same agent_id/trace_id, metadata carrying `branched_from_{run_id,checkpoint_id,turn}` → save the branch → `resume(branch.checkpoint_id)`.
**Invariant:** (1) Resume continues at `turn_index + 1` — checkpoint.messages already contain the paused turn's assistant response. (2) Identity continuity is genuine: same run_id/trace_id after resume, so cross-run attribution stays correct; only rollback mints a new run_id (session-tree semantics — original checkpoints are NEVER mutated or deleted). (3) Rollback tie-break is `(turn_index, list position)` max — latest saved wins among equal turns. (4) Unknown extension keys are silently dropped on restore (slot may not exist in this process). (5) KNOWN LIMITATION, documented in-source: a paused turn with MULTIPLE tool calls loses un-executed siblings' results (single-clarify-per-turn resumes cleanly); resuming mid non-ReAct LoopStrategy restarts that strategy's phase tracking from scratch — full support needs strategies to persist their own phase marker.
**Probe:** No direct test exercises resume.py in-repo (coverage caveat — deterministic source-grounding instead): graph search resolves all three functions at the cited lines; contract pinned by `AgentCheckpoint` model + `InMemoryCheckpointStore.latest/history` semantics (`modules/stores/checkpoint/in_memory.py:26-33`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "resume rollback checkpoint_store seed_context _resume_turn_index branched_from", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the same-instance re-entry pattern, `turn_index + 1` continuation, budget/todos/extensions restoration, and session-tree branching for time-travel; adapt the `_resume_*` private-kwarg plumbing to your run entry point, and decide explicitly whether multi-tool-call pause or loop-strategy phase persistence matters to you before adopting those limitations; omit `resume_thread` if your host always has concrete checkpoint ids. Coverage caveat: NO direct test — claims source-grounded; treat the documented limitations as real behavior boundaries, not edge-case trivia.

**Porting trap:** this module's `rollback(thread_id, turn_index)` restores AGENT-RUN state via checkpoints. It is NOT `GraphSkillStore.rollback(name, version)` (skill-content version restore, `app/agents/agent_loop/skills/graph_store.py:474`) and NOT the DB transaction rollbacks sprinkled through `api/routes/agent.py` — three unrelated operations sharing one verb.
