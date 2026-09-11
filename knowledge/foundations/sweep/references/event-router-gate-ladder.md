<!-- capsule-v2 -->
# Event-router gate ladder — which predicates route a webhook event, and where does precedence let a restart bypass everything?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** For each `(event, action)` pair, what exact gate chain decides whether the agent runs — and which compound boolean is a trap when porting?

## match/case router with per-case gate ladders
**Path/Symbol:** `sweepai/api.py:374-878` (`handle_event`), decisively `:517-543` (label auto-provision) and `:585-595` (restart precedence) (line range).
**Signature:** `def handle_event(request_dict, event)` — dispatches on `match event, action:` tuples.
**Data Shape:** Raw GitHub payload dict → pydantic models (`IssueRequest`, `IssueCommentRequest`, `CommentCreatedRequest`, `PRRequest`); gate inputs are label lists, `comment.user.type`, `BLACKLISTED_USERS`, and `request.changes.body_from`.

### Decisive source
```python
except GithubException as e:
    if e.status == 422 and any(error.get("code") == "already_exists" for error in e.data.get("errors", [])):
        logger.warning(f"Label '{GITHUB_LABEL_NAME}' already exists in the repository")
    else:
        raise e
```
```python
if (
    request.issue is not None
    and sweep_labeled_issue
    and request.comment.user.type == "User"
    and request.comment.user.login not in BLACKLISTED_USERS
    and not request.comment.user.login.startswith("sweep")
    and not (
        request.issue.pull_request and request.issue.pull_request.url
    )
    or restart_sweep
):
```

**Flow:** `handle_event` matches `(event, action)`: `issues/opened` auto-labels (creating the sweep label idempotently, tolerating 422 already_exists); `issues/{edited,labeled}`, `issue_comment/{created,edited}` route to `call_on_ticket` only through the full user/label/login/bot gate ladder; PR-bound comment cases route to `call_on_comment` via `should_handle_comment` (`body.lower().startswith("sweep:")`, human author, non-blacklisted, no BOT_SUFFIX).
**Invariant:** The restart branch compiles as `(A and B and C and D and E and F) or restart_sweep` — because `and` binds tighter than `or`, a bot-comment "Restart Sweep" button click bypasses EVERY other gate (label check, user type, blacklist, issue-vs-PR). That is intended for restart but is exactly the kind of precedence accident that silently changes semantics when gates are reordered or reformatted in a port. Bot-button detection additionally requires `request.changes.body_from is not None` — an edit event without body diff can never trigger a button.
**Probe:** Direct tests cover the button predicates consumed by this ladder: executed at pin `python3 -m unittest sweepai.utils.buttons_test -v` → 7 OK (`test_check_button_activated`: previously-toggled button returns False; `test_check_button_title_match`: title-in-old-body match). No test covers the boolean structure itself — coverage caveat; deterministic probe = parenthesize the compound condition by hand.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "handle_event github webhook event action dispatch", limit: 8 });
// executed at pin: #1 sweep.sweepai.api.handle_event api.py 374-878 (twin sweepai/watch.py handle_event also exists)
```

## Verdict
Adopt the `(event, action)` match structure, the idempotent-label-provision-with-422-tolerance, and the rule that bot-originated actions require an actual body delta; adapt gate predicates to your identity model; omit Sweep's specific labels/blacklist env plumbing. When porting, rewrite every mixed and/or ladder with explicit parentheses and a regression test on the restart path.
