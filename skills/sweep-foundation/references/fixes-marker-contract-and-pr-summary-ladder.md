<!-- capsule-v2 -->
# "Fixes #N.\n" marker contract & PR-summary ladder — how do you keep a bot-PR ↔ issue link that three independent readers can all parse, and what does the LLM title/description rewrite ladder actually do?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What exact string contract couples Sweep's PR bodies to its old-PR deletion, comment billing attribution, and Jira resolution links — and what are the failure modes of the regex rewrite ladder that produces those bodies?

## Two writers, three readers, one literal marker
**Path/Symbol:** WRITERS — `sweepai/core/pull_request_bot.py:PRSummaryBot.get_pull_request_summary` (:134–170, LIVE; called from `sweepai/handlers/on_ticket.py:642`) and `sweepai/utils/ticket_rendering_utils.py:rewrite_pr_description` (:368–386, DEAD TWIN — zero callers at pin). READERS — `sweepai/utils/ticket_rendering_utils.py:delete_old_prs` (:231–245, marker check at :242), `sweepai/handlers/on_comment.py:95`, `sweepai/handlers/on_jira_ticket.py:77`.
**Signature:** `get_pull_request_summary(problem_statement, issue_number, repo, overrided_branch_name, pull_request, pr_changes) -> pr_changes` (staticmethod on PRSummaryBot(ChatGPT)).
**Data Shape:** writer body = `f"{new_description}\n\nFixes" f" #{issue_number}.\n\n---\n{GHA_SUMMARY_START}{GHA_SUMMARY_END}\n\n{INSTRUCTIONS_FOR_REVIEW}{BOT_SUFFIX}"` (live) / `f"{new_description}\n\nFixes" f" #{issue_number}.\n\n---\n\n{INSTRUCTIONS_FOR_REVIEW}{BOT_SUFFIX}"` (dead twin); writer title = `f"Sweep: {new_title}"`; initial PR body is `""` (MockPR at on_ticket.py:632–640, "overrided later") overwritten before `repo.create_pull` (:656).

### Decisive source
```python
# WRITER (live) — the marker is SPLIT across two adjacent f-strings
pr_changes.title = f"Sweep: {new_title}"
pr_changes.body = (
    f"{new_description}

Fixes"
    f" #{issue_number}.

---
{GHA_SUMMARY_START}{GHA_SUMMARY_END}

{INSTRUCTIONS_FOR_REVIEW}{BOT_SUFFIX}"
)

# READER 1 — literal + bot-login gate (delete_old_prs :242)
if pr.user.login == CURRENT_USERNAME and f"Fixes #{issue_number}.
" in pr.body:

# READER 2 — regex, trailing dot is ANY char, no 
 anchor (on_comment.py :95)
issue_number_match = re.search(r"Fixes #(?P<issue_number>\d+).", pr_body or "")

# READER 3 — literal, page 0 only, NO bot-login gate (on_jira_ticket.py :77)
if f"Fixes #{github_issue.number}.
" in pr.body:
```

**Flow:** ticket completes → MockPR(body="") → get_pull_request_summary: up to 3 attempts (`for attempt in [0, 1, 2]`), each calls the LLM with issue + branch diff text, parses `<pr_title>`/`<pr_description>` XML tags (DOTALL); gate at :160 `if pr_desc_matches is None or pr_title_matches is None and attempt == 2:` → set title/body → create_pull with the marker-bearing body. Downstream: delete_old_prs finds the previous bot PR for the same issue by marker + bot login and safe-deletes its branch; on_comment recovers the original issue number from the marker for billing attribution; on_jira_ticket finds the resolution PR to link from the Jira comment.
**Invariant:** The marker `Fixes #N.
` (period + newline) is a cross-file string contract: two literal readers require it byte-exact, while the regex reader is looser (its trailing `.` matches any character, so "Fixes #N1" would also match). If a porter changes the writer format (e.g. GitHub-style "Fixes #N" without the period), the two literal readers silently break — old bot PRs are never deleted (branch leak) and Jira comments lose the PR link — while the regex reader keeps working: silent partial failure. The writers split the marker across two adjacent f-strings (`"...\n\nFixes"` + `" #{issue_number}.\n..."`), so a literal grep for "Fixes #" finds ONLY the three readers — audit the contract by grepping for the second half (`grep -rn '" #' ...` / `" #{issue_number}."`) or both halves separately. The :160 gate has an operator-precedence quirk: it parses as `(desc is None) or (title is None and attempt == 2)` — a missing DESCRIPTION returns the unchanged body on any attempt, but a missing TITLE on attempts 0/1 falls through to the else branch and crashes on `pr_title_matches.group(1)` (AttributeError on None). There is NO break on success: even a perfect first response burns all 3 LLM calls (last successful parse wins) — a port should break after the first fully-parsed response. The dead twin rewrite_pr_description must not be mistaken for a live path (zero callers at pin).
**Probe:** No offline-runnable test exists for this plane (live-GitHub harness only — standing block). Deterministic probes at pin: `grep -rn 'Fixes #' --include='*.py' sweepai/ | wc -l` → 3 (readers only); `grep -rn 'Fixes' --include='*.py' sweepai/ | grep -v '#'` → exactly the 2 writer lines (pull_request_bot.py:167, ticket_rendering_utils.py:383); `grep -c 'rewrite_pr_description' sweepai/utils/ticket_rendering_utils.py` → 1 (definition only, dead); `grep -n 'attempt == 2' sweepai/core/pull_request_bot.py` → :160; `grep -n 'Sweep: {new_title}'` → :165; `grep -rn 'get_pull_request_summary' --include='*.py' sweepai/ | grep -v def` → on_ticket.py:642 only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "get_pull_request_summary Fixes issue number pr body delete_old_prs", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// pull_request_bot.py:130-200, ticket_rendering_utils.py:368-395, on_comment.py:85-105,
// on_jira_ticket.py:65-90, on_ticket.py:630-660 at pin substituted — see verification.md pass 4.
```

## Verdict
Adopt the single-literal-marker design (one byte-exact substring as the cross-file join key), the per-reader strictness ladder (literal+login-gate for destructive cleanup, looser regex for attribution, page-0 literal for linking), and the XML-tagged LLM output with bounded retry. Fix the precedence quirk (parenthesize the gate), add a break-on-success, and keep the initial-empty-body-then-overwrite pattern only if your create path tolerates it. Adapt the "Sweep: " title prefix and GHA/review boilerplate to your product. Omit the dead twin writer entirely. Coverage caveat: no live direct test at pin; the marker contract is pinned only by the grep census above.
