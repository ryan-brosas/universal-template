<!-- capsule-v2 -->
# Slack Auto-Link Identity Binding — how does a first button click bind a Slack identity to a directory user without ever hijacking an existing binding?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you atomically link a channel identity to an existing account row on first interaction, race-safe and hijack-proof?

## Conditional UPDATE guarded on IS NULL, refuse-not-overwrite
**Path/Symbol:** `packages/python/awaithumans/server/services/user_service.py:132–181` — `link_slack_identity_by_email`; consumed by `_resolve_slack_user_with_auto_link` (`server/routes/slack/interactions.py:187`, path-2 auto-link); direct test `packages/python/tests/services/test_link_slack_identity.py` (4 tests).
**Signature:** `link_slack_identity_by_email(session, *, email: str, slack_team_id: str, slack_user_id: str) -> User | None`.
**Data Shape:** returns the updated row on success; `None` means exactly one of three things — no email match, row already bound to a DIFFERENT slack id, or (via `.returning`) lost conditional update. Caller maps None to a refusal hint, never to an error.

### Decisive source
```python
if user.slack_user_id and user.slack_user_id != slack_user_id:
    # Already bound to a DIFFERENT Slack user — refuse silently rather
    # than overwrite. (:146-150)
    return None
...
# Atomic conditional update — only patches the row when slack_user_id is
# still NULL (or matches). Two concurrent first-clicks for the same email
# race onto the same write; the second is a no-op against an already-bound
# row, correct either way. (:160-175)
result = await session.execute(
    update(User)
    .where(User.id == user.id,
           (User.slack_user_id.is_(None)) | (User.slack_user_id == slack_user_id))
    .values(slack_team_id=slack_team_id, slack_user_id=slack_user_id)
    .returning(User)
)
await session.commit()
return result.scalar_one_or_none()
```

**Flow:** email lookup → pre-check refuses different-binding rows → conditional UPDATE re-asserts the guard INSIDE the statement so two concurrent first-clicks converge (winner writes; loser's WHERE matches the now-equal binding or no-ops) → returning row feeds back into the interactions flow which logs `slack_identity_linked … via=first_click`. The in-route ladder adds the scope-aware refusals around this primitive: missing `users:read.email` email vs no-directory-match vs deactivated operator each get their own ephemeral text.
**Invariant:** NEVER overwrite an existing binding — the same guard exists twice (Python pre-check for fast refusal, SQL predicate for atomicity under races); the row-state truth is the SQL predicate, not the pre-check. This is the storage twin of the route-level auto-link ladder (see slack-interactivity-entry) — port them together or the route will promise bindings the store refuses.
**Probe:** `packages/python/tests/services/test_link_slack_identity.py` — `test_auto_link_refuses_when_slack_identity_taken` (:91) pins never-hijack; `test_auto_link_is_idempotent_when_already_correctly_bound` (:124) pins same-id re-bind success; unknown-email → None (:77).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "link_slack_identity_by_email slack_user_id IS NULL auto-link", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the double-guarded conditional UPDATE (application pre-check + SQL IS NULL/equals predicate + RETURNING) verbatim for any first-interaction identity binding. Adapt only the identity columns. Omit nothing — "refuse silently rather than overwrite" is stated as the design intent and pinned by its own test.
