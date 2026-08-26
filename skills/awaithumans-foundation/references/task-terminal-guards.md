<!-- capsule-v2 -->
# Terminal-State Guard — how do concurrent complete/cancel/timeout writers stay first-writer-wins?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does the server guarantee exactly one terminal transition when a human submission races the timeout scheduler or a second channel?

## Conditional UPDATE with rowcount as the lock
**Path/Symbol:** `packages/python/awaithumans/server/services/task_service.py:claim_task` (:254–326), `complete_task` (:329–481), `timeout_task` (:484–520), `cancel_task` (:523–558).
**Signature:** all follow `get_task → terminal-check → UPDATE … WHERE status NOT IN terminal → rowcount==0 ⇒ refresh+raise/no-op`.
**Data Shape:** `TERMINAL_STATUSES_SET = frozenset({COMPLETED, TIMED_OUT, CANCELLED, VERIFICATION_EXHAUSTED})` lives in `utils/constants.py`; audit rows record every transition with actor_type agent/human/system.

### Decisive source
```python
result = await session.execute(
    update(Task).where(Task.id == task_id)
        .where(Task.status.notin_(list(TERMINAL_STATUSES_SET)))
        .values(status=target_status, response=final_response, ...))
if result.rowcount == 0:
    # Race condition: another writer got there first
    await session.refresh(task)
    raise TaskAlreadyTerminalError(task_id, task.status)
```
Claim variant narrows further: `.where(Task.assigned_to_user_id.is_(None))` — loser's re-read tells them WHO won (`TaskAlreadyClaimedError(task_id, task.assigned_to_user_id)`), surfaced as an ephemeral "already claimed by X".

**Flow:** every mutation funnels through the same shape: pre-check (fast, friendly error) → conditional UPDATE (the REAL guard) → rowcount arbitration → audit entry → commit. `timeout_task` alone treats rowcount==0 as benign no-op (someone completed first — success semantics); complete/cancel/claim treat it as the typed error.
**Invariant:** the WHERE clause is authoritative, never the earlier SELECT — LLM verification runs seconds BETWEEN read and write, so only the conditional update closes the window. Post-verifier completion still passes through the same guarded UPDATE (:431–441).
**Invariant:** hard `delete_task` (:561–574) removes the row but deliberately leaves AuditEntry rows orphaned — evidence survives the subject.
**Probe:** `tests/tasks/test_verifier_integration.py` (:111–164 reject/resubmit/exhaust cycles), `tests/slack/test_claim_broadcast_e2e.py`, `tests/tasks/test_completer_attribution.py`; scheduler-side pin in `services/timeout_scheduler.py` (indexed `timeout_at <= now` sweep feeding `timeout_task`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "claim_task broadcast first writer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt conditional-UPDATE-with-rowcount for any human-raceable state machine, the loser-informing claim error, and the always-audit discipline. Adapt status vocabulary to your domain; keep the four-status terminal set closed. Omit FastAPI/SQLAlchemy specifics if porting to another stack — but keep the property "guard lives in SQL, not in app code."
