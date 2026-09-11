<!-- capsule-v2 -->
# Slack Installations Admin Surface — token never leaves, static workspace is cached, 204 has no body

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What does an operator-only Slack-management API expose, and which response-shape details does FastAPI punish you for forgetting?

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

**Flow:** every route behind require_admin (non-operator could otherwise DoS the integration via DELETE) → list maps rows through _to_public → uninstall returns True-rowcount-or-404 → members endpoint resolves team client (404 if no installation — detail names the fix: "Install the awaithumans app to this workspace first") then users.list (502 on scope/revocation, detail names `users:read` + reinstall path :188-195) → filter+sort for the picker UI (:197-214: drop deleted/is_bot/id==USLACKBOT, project profile fields, stable sort by `(real_name || name || id).lower()`). Installation UPSERTS overwrite in place (reinstalls are common; no versioning).
**Members plane (direct-tested):** `list_workspace_members` (:153-215) is a single un-paginated `users.list` call — NOT a pagination plane; docstring pins the operator contract: "Bots, deactivated accounts, and the Slackbot pseudo-user are filtered out so the picker only shows humans the operator can actually assign tasks to" (:169-171). Direct tests `tests/slack/test_workspace_members_route.py`: filter+order+shape :186-216 (U_ALICE/U_BOB kept; USLACKBOT/B_HOOK/U_GONE out; alphabetical; real_name/display_name/is_admin projected), 404-no-installation :219-234, 502-with-scope-hint :237-254.
**Invariant:** bot_token is encrypted-at-rest and absent from EVERY public shape; SlackApiError ⇒ 502-with-reinstall-hint, everything else propagates.
**Probe:** `packages/python/tests/slack/test_workspace_members_route.py` (`test_members_filters_bots_deactivated_and_slackbot`:186, `test_members_404_when_no_installation`:220, `test_members_502_when_slack_rejects`:238) + `tests/slack/test_installation_service.py` (`test_upsert_existing_overwrites`:35, `test_delete_removes_row`:82).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "list_workspace_members auth_test static workspace users_list", limit: 4 });
```
Live rank-1/2 line-exact (:157-215 + Route node); service rank hits cover upsert/delete.

## Verdict
Adopt admin-gating, token-absent public shapes, and the specific-catch rule; adapt endpoints to your surface; remember the 204/response_class detail verbatim if you stay on FastAPI — it's an easy 500.
