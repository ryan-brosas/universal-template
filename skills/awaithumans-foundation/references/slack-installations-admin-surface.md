<!-- capsule-v2 -->
# Slack Installations Admin Surface — token never leaves, static workspace is cached, 204 has no body

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** What does an operator-only Slack-management API expose, and which response-shape details does FastAPI punish you for forgetting?

## require_admin router-wide; auth.test result cached process-long; specific SlackApiError catches
**Path/Symbol:** `packages/python/awaithumans/server/routes/slack/installations.py` — gate rationale (:33-38), `_static_workspace_cache` (:46), `_to_public` (:49-59), `get_static_workspace` (:74-132), `uninstall_slack_workspace` (:135-150), `list_workspace_members` (:153-215); service twin `services/slack_installation_service.py` (upsert-overwrite :17-63, delete :78-84).
**Signature:** GET `/installations`, GET `/static-workspace`, DELETE `/installations/{team_id}` (204), GET `/installations/{team_id}/members`.
**Data Shape:** public shapes NEVER include bot_token; members filtered to humans only (drop deleted/is_bot/id==USLACKBOT), sorted stable by `(real_name || name || id).lower()`.

### Decisive source
```python
@router.delete("/installations/{team_id}", status_code=204,
    # Override the default JSONResponse — 204 forbids a response body, and
    # FastAPI's default response would try to emit one.
    response_class=Response)
...
except SlackApiError as exc:
    # Specific catch — bare `except Exception` would mask network / runtime
    # errors as "token rejected." Slack's own failures all surface as SlackApiError;
    # anything else is a genuine bug and should propagate to the central handler.
```
Static-workspace endpoint: 404 when SLACK_BOT_TOKEN unset ("dashboard can branch on absence cleanly"), 502 when Slack rejects the token; module-global cache because "env vars only change between restarts anyway."

**Flow:** every route behind require_admin (non-operator could otherwise DoS the integration via DELETE) → list maps rows through _to_public → uninstall returns True-rowcount-or-404 → members endpoint resolves team client (404 if no installation) then users.list (502 on scope/revocation) → filter+sort for the picker UI. Installation UPSERTS overwrite in place (reinstalls are common; no versioning).
**Invariant:** bot_token is encrypted-at-rest and absent from EVERY public shape; SlackApiError ⇒ 502-with-reinstall-hint, everything else propagates.
**Probe:** `packages/python/tests/slack/test_workspace_members_route.py` + `tests/slack/test_installation_service.py` (`test_upsert_existing_overwrites`:35, `test_delete_removes_row`:82). Suites green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "list_workspace_members auth_test static workspace users_list", limit: 4 });
```
Live rank-1/2 line-exact (:157-215 + Route node); service rank hits cover upsert/delete.

## Verdict
Adopt admin-gating, token-absent public shapes, and the specific-catch rule; adapt endpoints to your surface; remember the 204/response_class detail verbatim if you stay on FastAPI — it's an easy 500.
