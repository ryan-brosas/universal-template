<!-- capsule-v2 -->
# Checkpoint snapshot — what must a resumable agent checkpoint carry, and who stamps it?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What fields make an agent run resumable after a crash/HIL pause — and which ones are easy to forget (so the resume builds an invalid message or loses state)?

## One pydantic model + one save_checkpoint funnel, stamped at post-turn and at HIL pauses
**Path/Symbol:** `backend/python/app/agent_loop_lib/modules/stores/checkpoint/base.py` — `CheckpointKind` (:14-20), `AgentCheckpoint` (:23-60), `CheckpointStore` ABC (:63-92). Emitter: `backend/python/app/agent_loop_lib/agent/observability.py` `save_checkpoint` (:111-154); HIL pause stampers `handle_tool_approval` (:197-247) and `handle_clarify` (:250-299).
**Signature:** `async def save_checkpoint(agent, kind: str, goal, messages, turn_index, *, current_tool=None, hil_request_id=None, pending_tool_call_id=None) -> str | None`; `class AgentCheckpoint(BaseModel)` with `checkpoint_id (uuid4)`, identity quintet (`run_id`, `agent_id`, `parent_run_id`, `trace_id`, `spawn_depth`), `goal`, `messages`, `turn_index`, `budget_snapshot`, `kind ∈ {TURN_START, PRE_TOOL, POST_TOOL, TURN_COMPLETE, HIL_PAUSE, AGENT_COMPLETE}`, `session_id`, `status`, `hil_request_id`, `pending_tool_call_id`, `started_at`, `todos`, `extensions`.
**Data Shape:** Store ABC is 5 methods — `save(cp)->checkpoint_id`, `load(id)` (KeyError if missing), `latest(run_id)|None`, `history(run_id)` oldest-first, `delete_run(run_id)`. Reference backend is a dict-of-lists per run_id; File/SQLite/Redis/Postgres named as intended backends.

### Decisive source
```python
# The two fields that exist ONLY so resume() can build a valid provider message:
    # The ORIGINAL tool_use id of the clarify() call that triggered the HIL
    # pause. Needed on resume to build a valid TOOL-role message — providers
    # like Anthropic require tool_result.tool_use_id to match the assistant's
    # tool_use block, which is call.id, NOT the internal hil_request_id.
    pending_tool_call_id: str | None = None
    started_at: str | None = None   # original run start time, carried across resume
# ...and in save_checkpoint — the full-state capture that makes resume lossless:
        extensions=agent.scope.snapshot_extensions() if agent.scope is not None else {},
```

**Flow:** every post-turn → `save_checkpoint(..., kind="turn_complete")` with budget snapshot + todos + persisted StateSlot extensions; a HIL pause (`handle_clarify`/`handle_tool_approval`) additionally stamps `kind="hil_pause"`, `current_tool`, `hil_request_id`, AND `pending_tool_call_id=call.id` BEFORE blocking forever on `wait_for_response` — the checkpoint exists precisely because the process may die while blocked. `CHECKPOINT_SAVED` event emitted after each save.
**Invariant:** (1) Stores ALWAYS created in control plane composition — resume and the approval hook depend on them even when observability stores are off. (2) `pending_tool_call_id` must be the ORIGINAL provider-visible tool_use id, never the internal hil_request_id — Anthropic-style providers reject mismatched `tool_result.tool_use_id`. (3) `started_at` carries the original wall-clock start across resumes (elapsed-time budgets stay truthful). (4) `messages` holds the FULL context window at checkpoint time including the assistant turn whose tool_use triggered the pause. (5) `status` stored as plain string to avoid a circular import. (6) `save_checkpoint` returns `None` silently when no store configured — callers never branch on it.
**Probe:** `backend/python/tests/unit/agents/adapter/test_hooks.py` (HIL pause path); store contract pinned by `InMemoryCheckpointStore` (`modules/stores/checkpoint/in_memory.py:9-36`). Coverage caveat: no dedicated unit test for `base.py` field semantics; claims are source-grounded from model + emitter.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "AgentCheckpoint CheckpointStore save_checkpoint hil_pause pending_tool_call_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the field set as the minimal resumable-snapshot contract (identity quintet + budget + todos + extensions + dual-id HIL pair), the always-created-store rule, and the pause-before-wait stamping order; adapt kind names, storage backends, and event emission to host; omit PRE_TOOL/POST_TOOL/AGENT_COMPLETE kinds until a host need appears (only TURN_COMPLETE + HIL_PAUSE are emitted today). Coverage caveat: base.py itself untested directly; contract verified via emitter source + InMemory reference backend.
