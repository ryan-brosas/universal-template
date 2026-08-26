<!-- capsule-v2 -->
# Post-Completion Message Update — stale interactive Slack buttons are a trust bug, not a papercut

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** How do you retire every action-button message once its task reaches a terminal state without ever failing the task lifecycle?

## Snapshot-in, fan-out chat.update, swallow everything but import errors
**Path/Symbol:** `packages/python/awaithumans/server/channels/slack/post_completion.py` — module docstring contract (:1-21), `_handoff_for_task` (:119-125), `_resolve_client` (:128-137), `update_slack_messages_for_task` (:50-116).
**Signature:** `async update_slack_messages_for_task(task_id: str) -> None` — takes ONLY the id because the route's session may be closed by background-run time; all other values are re-read from a fresh session inside.
**Data Shape:** iterates `SlackTaskMessage` rows `(channel, ts, team_id)` recorded by the notifier at post time; terminal surface = `terminal_message_blocks(...)` with NO buttons.

### Decisive source
```python
# The "View in dashboard" button on the terminal surface must also be a signed
# handoff URL when we know who the assignee is ... When the task has no resolved
# assignee (broadcast that nobody claimed before cancel/timeout), we drop back
# to the unsigned URL.
handoff = _handoff_for_task(task)
review_url = build_review_url(task_id=task.id, params=handoff)
...
client = await _resolve_client(team_id=msg.team_id, session=session)
if client is None:
    logger.info("post_completion: no Slack client for team=%s; skipping message ts=%s", ...)
    continue          # never fall back to the DEFAULT workspace in multi-workspace setups
```
`_handoff_for_task` returns None unless BOTH `assigned_to_user_id` and `timeout_at` exist; expiry = `task_handoff_expiry(task.timeout_at)` — the link dies WITH the task.

**Flow:** fire-and-forget background task (FastAPI BackgroundTask or scheduler-created asyncio task — outside Slack's 3s view_submission budget, else Slack re-delivers and double-completes) → fresh session → load task (failure ⇒ log+return) → list recorded messages (empty ⇒ return) → build ONE review_url for all messages → per message resolve team-scoped client → chat.update with button-less blocks → per-message exceptions logged-and-swallowed.
**Invariant:** best-effort throughout — SQL/missing-task/revoked-install/update failures are UI papercuts and must never propagate; only a module-import failure is fatal. The no-fallback rule in `_resolve_client` prevents cross-tenant posts when an installation was revoked mid-flight.
**Probe:** `packages/python/tests/slack/test_post_completion.py` (`test_updates_every_recorded_message`:124, `test_no_messages_means_no_calls`:153, `test_chat_update_failures_are_swallowed`:175, `test_posted_blocks_have_no_action_buttons`:203) — 19 passed incl email-token/stats/notification-audit suites at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "update_slack_messages_for_task terminal_message_blocks chat_update", limit: 5 });
```
Live rank-2 line-exact (:50-116); rank-1 resolves the block builder it calls.

## Verdict
Adopt the snapshot-by-id signature, single-review-URL-per-task reuse, and total-swallow error posture; adapt the terminal-block builder to your own surface vocabulary; omit the team-scoped-client resolution only if you are genuinely single-workspace (and record that boundary).
