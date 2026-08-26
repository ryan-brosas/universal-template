<!-- capsule-v2 -->
# Slack Message Ledger — record-then-update needs no uniqueness constraint

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** What does the persistence layer for "Slack messages we posted about a task" need — and deliberately NOT need?

## Tiny DAL beside the model; duplicate row = harmless double chat.update
**Path/Symbol:** `packages/python/awaithumans/server/channels/slack/message_log.py` — design docstring incl no-unique-constraint ruling (:1-12), `record_posted_message` (:29-52), `list_messages_for_task` (:55-66); model `server/db/models/slack_task_message.py`.
**Signature:** `record_posted_message(session, *, task_id, channel, ts, team_id) -> None` (caller commits); `list_messages_for_task(session, task_id) -> list[SlackTaskMessage]`.
**Data Shape:** rows `(task_id, channel, ts, team_id)`; ORDER BY created_at ASC so callers don't depend on PK accidents.

### Decisive source
```python
# We do not enforce a unique constraint on (task_id, channel, ts) — a
# duplicate row is harmless (the post-completion updater runs chat.update
# twice with the same payload, second is a no-op) and the extra index would
# slow inserts on the hot path.
if not channel or not ts:
    logger.warning("record_posted_message: missing channel/ts for task=%s; skipping", task_id)
    return                      # Slack returned an unexpected shape; skip useless refs
```
Best-effort insert: if the task was deleted between post and write, log and move on — never fail the notification path on bookkeeping.

**Flow:** notifier posts → records one row per chat.postMessage (same session/commit as the notify transaction) → later, post_completion loads ALL rows and chat.update's each to the terminal surface. Duplicate ⇒ idempotent second update.
**Invariant:** hot-path inserts carry no unique index BY DESIGN; missing channel/ts skips the row rather than storing garbage; consumer (post-completion-message-update capsule) treats every row as best-effort.
**Probe:** graph pins both functions line-exact; behavioral coverage via `tests/slack/test_post_completion.py:test_no_messages_means_no_calls`:153 + `test_updates_every_recorded_message`:124 (ledger round-trip through the fake client).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "record_posted_message list_messages_for_task SlackTaskMessage", limit: 4 });
```

## Verdict
Adopt the ledger shape and the documented decision to skip uniqueness; adapt columns to your message metadata; if your updater is NOT idempotent, you must add the constraint this repo deliberately omitted.
