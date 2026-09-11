<!-- capsule-v2 -->
# Slack Interactivity Entry — what must the /interactions webhook do between signature check and task completion?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you turn Slack button clicks and modal submissions into authorized, race-safe task claims and completions?

## Raw-body-twice verification, authorize-before-modal, 3-second submission budget
**Path/Symbol:** `packages/python/awaithumans/server/routes/slack/interactions.py` — `slack_interactions` (:76–111 raw body read twice), `_handle_block_actions` (:117 claim-priority ordering), `_resolve_slack_user_with_auto_link` (:187 three-path identity resolution), `_slack_user_can_act_on_task` (:272), `_handle_claim` (:355), `_ephemeral_reply` (:503 response_url ladder), `_handle_view_submission` (:556); direct test `packages/python/tests/slack/test_interactions_e2e.py` (13 tests).
**Signature:** `slack_interactions(request, session) -> dict | None`; returns `None` for block_actions, `{}` to close a modal, or `{"response_action": "errors", "errors": {...}}` for inline rejection.
**Data Shape:** body is `application/x-www-form-urlencoded` with ONE `payload` field whose value is a JSON string; modal task id rides in `view.private_metadata`.

### Decisive source
```python
body = await request.body()                      # bytes → HMAC over RAW body
if not verify_signature(body=body, timestamp=..., signature=..., signing_secret=...):
    raise HTTPException(status_code=401, detail="Invalid Slack signature.")
form = await request.form()                      # SAME body parsed again as form
payload = json.loads(form.get("payload"))
...
# view_submission :588-592 — inline rejection via response_action, task untouched:
if not authorised:
    return {"response_action": "errors", "errors": {"awaithumans:_auth": why_not}}
...
# :624 — fire-and-forget surface swap OUTSIDE the 3s budget:
asyncio.create_task(update_slack_messages_for_task(task_id))
```

**Flow:** block_actions dispatch checks CLAIM action FIRST ("Claim" beats "Open review" on broadcast cards with both buttons) → claim path = first-clicker-wins via `claim_task` (`TaskAlreadyClaimedError` carries `claimed_by_user_id`, surfaced as ephemeral "Already claimed by …"), then best-effort `chat_update` swaps the card for everyone else, then the modal pops for the winner. Direct-DM open-review path authorizes BEFORE opening the modal that could complete the task. Identity resolution is three-path: direct (team_id, slack_user_id) hit → first-click auto-link via `users.info` email + conditional bind → refuse with channel-specific hints (missing scope vs no directory match vs deactivated). Ephemeral replies go through Slack's short-lived `response_url` via plain httpx POST (no bot token needed) and fall back to `chat_postEphemeral`.
**Invariant:** (1) HMAC MUST be over the raw request body, not the parsed form — hence reading the body twice. (2) Missing `SLACK_SIGNING_SECRET` = 503 (config error, not auth failure); bad/stale signature = 401. (3) The claim gate does NOT need per-user authorization (first-click-wins BY DESIGN) but the DM-open and view_submission paths DO — anyone in a shared channel who saw the message must not complete someone else's task. (4) Auto-link never hijacks: bind happens only when `slack_user_id IS NULL` or already equal. (5) A slow `chat.update` inside view_submission would blow Slack's 3-second response window and cause re-delivery → DOUBLE completion; hence the fire-and-forget create_task. (6) Only httpx/SlackApiError are swallowed as best-effort; real bugs propagate.
**Probe:** `packages/python/tests/slack/test_interactions_e2e.py` — `test_view_submission_blocked_for_non_assignee_non_operator` (:497) asserts `response_action == "errors"` (:537) against a live app + FakeSlackClient; signature matrix (:253–306: missing/bad/stale/unset-secret), missing payload 400 (:309), silent no-form (:383), unknown payload type no-op (:563).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "slack_interactions _handle_claim _handle_view_submission response_action", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt raw-body-twice HMAC, claim-first action disambiguation, authorize-before-modal and before-submission, the response_url→postEphemeral fallback ladder, and the fire-and-forget post-completion surface swap verbatim. Adapt identity auto-link only together with its storage twin (`link_slack_identity_by_email`, see slack-auto-link-identity-binding). Omit nothing — each guard here maps to a named incident class (#144 auto-link, double-completion via slow chat.update).
