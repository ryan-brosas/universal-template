<!-- capsule-v2 -->
# Completer Attribution Authorize-First — who completed this task when the client can't be trusted to say?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you stamp completer identity server-side across four caller channels (dashboard session, admin bearer, embed token, Slack/email) without letting any caller forge it?

## Connected graph-selected seam
**Path/Symbol:** `packages/python/awaithumans/server/routes/tasks.py` — `complete_task_route` (:328-408) + `_session_user_email` (:411-422).
**Signature:** `async def complete_task_route(task_id, body: CompleteTaskRequest, request, background_tasks, session) -> TaskResponse` / `async def _session_user_email(request: Request, session: AsyncSession) -> str | None`.
**Data Shape:** attribution triple stamped by the SERVICE: `completed_by_email` (body-supplied only for non-cookie callers), `completed_by_user_id` (from `caller_user_id(request)`), `completed_via_channel`; plus audit kwargs `channel/embed_sub/embed_jti`.

### Decisive source
```python
    # Authorise BEFORE running the verifier — a non-assignee
    # submitting via the dashboard form would otherwise burn an
    # attempt and ship the (potentially sensitive) payload to the LLM.
    existing = await get_task(session, task_id)
    require_task_complete(request, existing)

    completer_email = body.completed_by_email
    if not completer_email:
        completer_email = await _session_user_email(request, session)

    # Stamp the user_id from the session cookie too — for Slack-only
    # users (no email column), email-only attribution leaves the audit
    # trail showing "—" ...
    completer_user_id = caller_user_id(request)
```
And the fan-out gate (:392-400):
```python
    # ... REJECTED is non-terminal, the agent shouldn't get a
    # "complete" callback for a verifier-rejected attempt — only
    # enqueue on a real terminal. Enqueue inline so the row is
    # committed in the same unit of work as the task transition ...
    if task.status in TERMINAL_STATUSES_SET:
        await enqueue_completion_webhook(session, task)
```
`_session_user_email` returns None unless `request.state.auth_claims` is `SessionClaims` (:418-420) — cookie callers only; admin bearer / magic-link / channel callers supply their own email through their own paths.

**Flow:** embed-bearer path FIRST (:347-366): scope mismatch ⇒ 403 `task_outside_token_scope`, completes with `completed_by_user_id=None` + channel/embed audit kwargs. Cookie/bearer path: authorize (`require_task_complete`) BEFORE the verifier runs → email falls back body → session claims → user_id stamped from caller → `complete_task(...)` → webhook enqueue + Slack surface swap BOTH gated on `TERMINAL_STATUSES_SET`. The Slack view-submission consumer mirrors this by resolving identity from the DIRECTORY ROW, never Slack's @handle.
**Invariant:** attribution is SERVER-DERIVED; the client's `completed_by_email` is accepted only where no stronger claim exists (and the route docstring says why: "the dashboard form doesn't [supply it] — why would the browser lie about who it is"). Authorization precedes verification so a rejected non-assignee burns neither an attempt nor LLM tokens. REJECTED is non-terminal: no callback, no surface swap.

**Probe:** `packages/python/tests/tasks/test_completer_attribution.py` — `test_dashboard_completion_stamps_user_id` (:69-89, email AND user_id AND display_name all asserted), `test_slack_only_completer_renders_display_name` (:92-141, service-level completion with `completed_by_user_id`, GET shows "TA"/U_TA_REAL_ID instead of "—"), `test_completed_by_falls_back_to_slack_id_when_no_display_name` (:144-198, renders "@U_NO_NAME").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "complete task completer attribution completed_by_email session claims authorize verifier", limit: 6 });
```
Live at pin: `test_slack_only_completer_renders_display_name` −28.47 (:92-141); fixture `slack_only_user` −27.42; `test_dashboard_completion_stamps_user_id` −25.97 (:69-89); `complete_task_route` −22.21 (:329-408); `_session_user_email` −17.12 (:411-422).

## Verdict
Adopt authorize-before-expensive-work and the server-derived attribution triple; treat the audit-visible identity (email ∪ user_id ∪ display_name fallback chain) as part of the product contract, not logging hygiene. Adapt the claim source to your auth surfaces. Omit the terminal-gated enqueue only if your transport has its own rejection filter — otherwise rejected attempts page the agent forever.
