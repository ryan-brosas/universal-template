<!-- capsule-v2 -->
# GHA autofix attribution chain — who is accountable for a bot-authored failing PR, and when may auto-fix fire?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** Given a failed CI run on a PR, what preconditions and human-attribution ladder must hold before an agent may autonomously push a fix?

## check_run/completed precondition stack + three-hop attributor fallback
**Path/Symbol:** `sweepai/api.py:388-457` (`handle_event`, case `"check_run", "completed"`) (line range); helpers `sweepai/handlers/on_check_suite.py` `download_logs:52-77`, `clean_gh_logs:235-252`.
**Signature:** case body inside `def handle_event(request_dict, event)`; `download_logs(repo_full_name, run_id, installation_id) -> str`, `clean_gh_logs(logs) -> (logs, user_message)`.
**Data Shape:** `CheckRunCompleted` pydantic payload; PR age from `pr.created_at.timestamp()`; comment-count scan of `pr.get_issue_comments()`; status list of base-branch head commit.

### Decisive source
```python
attributor = request.sender.login
if attributor.endswith("[bot]"):
    attributor = commit.author.login
if attributor.endswith("[bot]"):
    attributor = pr.assignee.login
if attributor.endswith("[bot]"):
    return {"success": False,
            "error_message": "The PR was created by a bot, so I won't attempt to fix it."}
```
```python
if (
    not (time.time() - pr.created_at.timestamp()) > 60 * 15
    and request.check_run.conclusion == "failure"
    and pr.state == "open"
    and get_gha_enabled(repo)
    and len([c for c in pr.get_issue_comments() if "Fixing PR" in c.body]) < 2
    and GHA_AUTOFIX_ENABLED
):
```

**Flow:** failing check_run on a PR-linked check → if the PR is a `[Sweep Rules]`/`[Sweep GHA Fix]` title older than 1h with any failed suite, it is closed outright → otherwise the seven-clause precondition stack gates a fix attempt (fresh PR ≤15min, open, gha_enabled, fewer than two prior fix comments, feature flag) → base branch must itself be passing (all head-commit statuses ≠ failure) before logs are downloaded and cleaned → attribution resolves sender→commit-author→assignee, refusing when all three are bots → free-tier users refused via `chat_logger.use_faster_model()` unless self-hosted.
**Invariant:** An agent never fixes a bot's PR, never fixes onto a red base, and never retries a fix more than twice (comment cap). Note the parenthesization trap in clause one: `not (age) > 60*15` parses as `(not age) > 900` — truthy-age makes `not age` False so the clause passes for fresh PRs; it works by accident of Python bool/int comparison and must not be "cleaned up" casually.
**Probe:** Direct test exists but is live-network: `tests/test_gha_extraction.py` calls `download_logs`/`clean_gh_logs` at module import with hardcoded RUN_ID + INSTALLATION_ID — blocked offline, recorded as standing runner block; deterministic probe = the executed graph retrieve below plus reading the fallback chain order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "check run failure logs download clean gha fix", limit: 8 });
// executed at pin: #1 download_logs on_check_suite.py 52-77, #2 clean_gh_logs :235-252,
// #3 test_gha_extraction TESTS edge visible in TESTS-edge query
```

## Verdict
Adopt the attribution fallback chain ending in explicit refusal, the red-base refusal, and the bounded retry cap as safety contracts; adapt the age windows and comment markers to your product; omit Sweep's specific env flags. Fix the accidental `not (x) > y` precedence with explicit parens — but only alongside a test pinning current behavior.
