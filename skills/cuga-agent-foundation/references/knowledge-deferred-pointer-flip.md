<!-- capsule-v2 -->
# Deferred pointer flip — why must a reindex promote its new collection only after ALL workers succeed AND the engine config still matches?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** The HTTP response returns before reindex finishes — what gate decides whether the active-collection pointer may move, and why is one-failure-enough to refuse?

## Wait-for-terminal → strict all-success → hash-still-matches → flip under lock → persist
**Path/Symbol:** `src/cuga/backend/server/manage_routes/knowledge_reindex.py:63-186` (`deferred_reindex_complete_and_flip`), migration entry `:189-299` (`migrate_and_reindex_for_agent`, Path A copy + source-flag-for-whole-lifetime), durable persist `:14-60` (`persist_active_vector_config`), wall-clock cap `_DEFERRED_FLIP_TIMEOUT_S = 30*60` at `:15-16`.
**Signature:** `async def deferred_reindex_complete_and_flip(agent_id, live_engine, live_state, target: str, target_hash: str, task_ids: list[str]) -> None`; poll loop sleeps 0.5s while `target in live_engine._reindex_in_progress`.
**Data Shape:** Task rows `{task_id, status ∈ completed|failed|cancelled}`; promotion writes `live_state.knowledge_config_hash = target_hash`; missing task rows counted as NOT done.

### Decisive source
```python
# knowledge_reindex.py:139-152 — STRICT mode and the concrete data-loss repro
# STRICT mode: refuse promotion unless every task succeeded. PERMISSIVE
# mode ("promote on any success") silently loses data — concrete repro:
# switching fastembed -> watsonx/e5, one file hit 518>512, 4/5 succeeded,
# pointer flipped, and search for that file's content returned nothing.
# Strict choice: stay on the old collection (all files have working
# vectors), surface the failure via task status, let the user retry.
if n_failed > 0:
    ...  # NOT promoting; old collection stays active
```
Four refusal gates run in order, each with a distinct operator log line: (1) workers didn't terminate before the 30-min cap; (2) a task row is MISSING from the listing (`len(relevant) != len(task_id_set)`) — a dropped/GC'd record must not let the flip fire early; (3) any failed/cancelled task (strict, quote above); (4) zero completions. Then the fifth gate INSIDE `agent_draft_lock(agent_id)`: engine's live `vector_config_hash()` must still equal `target_hash` — an SDK/Layer-bypass config change mid-reindex means the target collection no longer matches what queries will embed with.

**Flow:** `migrate_and_reindex_for_agent`: flag SOURCE for the WHOLE Path-A lifetime (not just the copy window — releasing after copy left a window where an upload landed in SOURCE only and was lost on flip) → copy source files under BOTH collection locks → `engine.reindex(target)` returns task_ids immediately → spawn `_flip_then_release_source()` background task → HTTP responds now. Flip task: wait busy-flag clear → snapshot statuses → five gates → set pointer → `persist_active_vector_config` writes vector-affecting fields AND hash into draft + published config so the flip survives restart (best-effort: in-memory flip already happened). Source flag released in wrapper's `finally` so it can never leak.
**Invariant:** The active pointer is integrity-critical: it may move only when the target provably contains a full successful re-embed of the same files AND the engine's current embedder still hashes to the target. Old collection remains authoritative through every failure path.
**Probe:** `tests/unit/test_knowledge_reindex_in_progress_guard.py:186-213` (promote when all complete), `:216-240` (refuse when all failed — "pointer must NOT have moved"), `:242+` (refuse when engine moved on), `:270` (waits for in-progress then flips), `:307` (refuse while a task still running), `:340` (bails at wall-clock deadline), `:373` (persists hash + embedder fields behaviorally).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "deferred_reindex_complete_and_flip migrate_and_reindex_for_agent knowledge_config_hash agent_draft_lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deferred-flip pattern (respond fast, promote behind the scenes) with strict all-success + config-hash-recheck gates and durable persistence of both fields-and-hash together. Adapt collection-naming (`kb_agent_<id>_<hash>`) to your scheme. Omit the FastAPI/route plumbing around it.
