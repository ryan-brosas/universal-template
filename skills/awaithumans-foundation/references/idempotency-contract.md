<!-- capsule-v2 -->
# Idempotent Task Contract — how does `await_human` stay resumable across agent crashes?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** When an agent crashes mid-await and re-invokes with the same key, why must the server look up tasks of ANY status — and what does a porter get wrong?

## Stripe-style lookup-any-status idempotency
**Path/Symbol:** `packages/python/awaithumans/server/services/task_service.py:create_task` (:40–150) + `_find_task_by_idempotency_key` (:621–631); SDK key derivation `packages/python/awaithumans/client.py:_generate_idempotency_key` (:311–318).
**Signature:** `create_task(session, *, task, payload, payload_schema, response_schema, timeout_seconds, idempotency_key, ...) -> tuple[Task, bool]` (bool = was_newly_created).
**Data Shape:** key = sha256(canonical JSON `{task, payload}`)[:32]; server returns `(existing_task, False)` on ANY key hit — active OR terminal (`completed/timed_out/cancelled/verification_exhausted`).

### Decisive source
```python
# Looking up ANY status (including terminal) is what makes direct mode
# resumable across agent restarts.
existing = await _find_task_by_idempotency_key(session, idempotency_key)
if existing is not None:
    return existing, False
...
try:
    await session.commit()
except IntegrityError:
    # Race: another request inserted with the same key between our SELECT
    # and INSERT. Roll back and return the existing task.
    await session.rollback()
    existing = await _find_task_by_idempotency_key(session, idempotency_key)
    if existing is not None:
        return existing, False
    raise
```

**Flow:** derive-or-take key → SELECT by key → hit ⇒ return stored task (agent resumes from `response` or gets the typed terminal error) → miss ⇒ route + INSERT → IntegrityError ⇒ rollback, re-select, return winner's row. The `was_newly_created` bool exists so the route fires notification side effects ONCE — replaying notifications on every retry would spam Slack/email.
**Invariant:** same key ⇒ same task forever, regardless of status. A NEW attempt after a terminal outcome requires a DISTINCT key (`f"{base}:retry-1"`). Never create duplicates under concurrency — the DB unique constraint + IntegrityError fallback is the arbiter, not the pre-check.
**Probe:** `packages/python/tests/tasks/test_idempotency_after_terminal.py` (:64–72 duplicate-while-active, :76–97 recover-after-completed returns response, :99–135 terminal statuses returned not recreated, :157–235 creation-vs-existing signal). Wire-level pin: `test_idempotent_replayed_header.py` (:32–70) — status stays **201** on replay; awareness travels in an `Idempotent-Replayed: true` header instead.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "idempotency key create_task", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lookup-any-status + IntegrityError race fallback + 201-on-replay-with-header; adapt key derivation to your payload canonicalizer (sorted keys, no whitespace — see TS twin `internal/idempotency.ts` canonicalStringify pinned by `tests/idempotency.test.ts` order-independence cases); omit the AwaitVerify managed-backend variant (idempotency reserved Phase 3 there). Coverage caveat: none — direct tests exist.
