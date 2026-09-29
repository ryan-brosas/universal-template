# Sourcebot patch-review workflow

Use the native Sourcebot review bot for required external PR review. CodeRabbit
is explicit opt-in tooling, not a prerequisite or fallback. Local tests, IDE
inspection and structural review remain required by
[pre-PR validation](../../pre-pr-validation/README.md).

## Keep the stages separate

The native GitHub bot consumes a published PR diff and posts findings to that
PR. It does not expose a local/uncommitted-diff review tool over MCP. Sourcebot
`ask_codebase` supplies indexed research, not this review receipt.

Finish local verification first. Before a PR exists, or while changes are still
unpushed, record bot review as PENDING with that reason. Local readiness permits
an authorized push/PR; it is not complete PR verification or permission to merge.
[Push PR](../../push-pr/README.md) owns publication, triggering and feedback.
A push-only/no-PR request stops without creating a PR or claiming bot coverage.

## Check readiness and trigger deliberately

1. Confirm the repository, PR, base/head SHAs, complete authored diff and expected
   bot identity. Existing reviews do not cover additional working-tree changes.
2. Verify the installed integration using
   [model and App setup](ask-models-and-agents.md#experimental-code-review-agent).
   Inspect existing host configuration before creating another App. Confirm the
   selected model, repository installation, webhook delivery and key access. Also
   prove an existing changed file is readable through Sourcebot at the exact PR
   head: the bot fetches file context there, not merely from the default branch.
   If missing, report the repository/head sync gap; working Ask or readable main
   is insufficient. Do not expand the corpus or force a sync without permission.
   Host configuration owns credentials, endpoint, command and automation policy.
3. Reuse a completed review only when its scope and revision still match. For
   manual review, an authorized PR comment must contain exactly the configured
   command (default `/review`). Read the actual command; do not assume it. If an
   auto-review is already running for this revision, observe it instead of
   triggering a duplicate.
4. Triggering uploads PR context to the configured model and causes bot comments.
   A read-only verification request only inspects existing evidence. Missing
   authorization, App installation or operator access is a named blocker, not
   permission to post, install, restart services or expose secrets.

## Establish completion, not just activity

Record the run/trigger evidence, bot identity, PR/base/head, reviewed paths and
coverage limits. Read findings and validate them against current source/tests.
Fixes invalidate affected evidence; re-review the final published revision.
Replies and resolution follow
[review threads](../../push-pr/references/review-threads.md).

Check the installed version's real completion signal. A webhook HTTP 200,
configured Agents card, working Ask call, empty findings list or elapsed wait
is not proof of success. Inline comments tied to `commit_id` prove those
findings' revision, not completion of the whole review. Skipped paths, partial
runs and generation/posting errors remain coverage gaps.

At upstream revision
[`b4931510`](https://github.com/sourcebot-dev/sourcebot/tree/b4931510050233e940992773468afd4252ebc89f),
the bot deliberately emits no clean-review comment and can catch generation or
comment-posting failures while continuing. Even its final posting log can follow
errors. See
[review rules](https://github.com/sourcebot-dev/sourcebot/blob/b4931510050233e940992773468afd4252ebc89f/packages/web/src/features/agents/review-agent/app.ts#L15-L23),
[generation](https://github.com/sourcebot-dev/sourcebot/blob/b4931510050233e940992773468afd4252ebc89f/packages/web/src/features/agents/review-agent/nodes/generatePrReview.ts#L13-L52)
and [posting](https://github.com/sourcebot-dev/sourcebot/blob/b4931510050233e940992773468afd4252ebc89f/packages/web/src/features/agents/review-agent/nodes/githubPushPrReviews.ts#L7-L39).
Do not equate silence or one comment with a complete clean review. Use available
runtime evidence correlated to the exact PR run and full diff, including errors
and omissions. If the deployment cannot establish completion and coverage, report
BLOCKED and the missing evidence; do not invent a status API or substitute Ask.
Do not enable sensitive prompt logging just to manufacture a receipt.

## Troubleshoot `/review` silence, failed runs and stuck status

Start from the public PR, then correlate runtime evidence; do not guess from one
signal. A user-visible `/review` comment followed by a bot `RUNNING`/status
comment proves trigger delivery and startup only. It is not automatic-review
completion, and repeated `/review` comments can start duplicate stuck runs.
Observe the existing run unless logs prove it is terminal or stale.

For a GitHub PR that shows no findings:

1. Read PR issue comments, review comments and reviews. Confirm the exact trigger
   comment, bot identity, base/head and whether any inline comments are tied to
   the current `commit_id`. CodeRabbit or another bot's prompt is unrelated to
   Sourcebot's native review state.
2. Verify Sourcebot can read at least one changed file at the exact PR head. If
   the runtime logs show repeated `File "..." not found in repository` for
   changed paths, the webhook and App may be working while the review agent's
   local file-context path is racing or missing the PR head. Verify the review's
   exact-head checkout before a single retrigger, or repair the integration to
   fetch exact-head GitHub content; readable `main` or working Ask is insufficient.
3. Inspect bounded Sourcebot/relay logs for the run id/time. `Review agent review
   command received` plus `Received a pull request event` means the command was
   accepted. `github_push_pr_reviews` completing with no GitHub review comments
   can still mean all hunks failed generation or nothing was posted. GitHub
   security-advisory signature warnings are noise unless the target event failed.
4. For a status comment stuck on `RUNNING`, check only safe log metadata first:
   file size/mtime and prompt/response counts, not private prompt contents. Moving
   mtime shows log activity, not necessarily progress in the target run. Stale
   mtime with unmatched prompts can suggest a hung model call; matched counts
   narrow investigation toward posting/status updates or process exit. Correlate
   these clues with the exact run before diagnosing the cause.

A Sourcebot-only restart can cancel a hung in-process review, but it leaves any
existing `RUNNING` comment stale unless the implementation has durable cleanup.
Before retriggering, fix or confirm timeout, duplicate-in-flight and final-status
behavior: every run should update to `COMPLETE`, `INCOMPLETE`, `FAILED` or
`SUPERSEDED` for the exact revision. Large/generated diffs may legitimately take
longer than small PRs, especially when the deployed agent processes hunks serially
and posts only after generation completes; verify that implementation's behavior.

Report local checks and bot status separately:

- **PENDING:** no published PR/revision yet, or an identified run is still active.
- **PASSED:** completion and coverage established for the current PR base/head,
  every finding dispositioned, and no unresolved blocking finding or omitted path.
- **BLOCKED:** missing access/configuration, failed or unverifiable completion,
  partial coverage, or unresolved blocking findings. Explain the recovery needed.

Pending or blocked bot review prevents claiming complete PR verification or
merging; it does not prevent authorized publication needed to obtain or repair
that review. Native bot review complements rather than replaces required CI and
local behavioral proof.
