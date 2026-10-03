---
description: Verify the current work actually works
argument-hint: "[scope]"
---
Check whether the current work meets what we asked for. Challenge the chosen
approach against current source and the actual patch, not only the plan summary.
When correctness depends on code structure, callers or comparable
implementations, use Sourcebot's ask_codebase tool to challenge the approach
against the indexed baseline; work with no indexed baseline needs direct evidence
instead. Reuse a valid brief rather than repeating a call per phase, and
honor an explicit request for that tool. If Sourcebot is unavailable or unhelpful
for a question that genuinely needs it, say so and rely on local execution
without implying indexed corroboration. Execution, not the index,
proves the local patch. For external patch review, use the Sourcebot review bot,
not CodeRabbit, through the
[review workflow](../knowledge/playbooks/sourcebot/references/review-workflow.md).
Report local verification separately from the PR-bound bot status; unpublished
changes and indexed Ask answers do not count as bot-reviewed. Run the relevant
checks and tell me what passed, what failed, and what remains untested. Judge each
check by the status it reported, not by the pipeline around it: without `pipefail`, a command piped through
`tail`/`grep`/`head` returns the last command's status, while with `pipefail`
an earlier command's failure can determine the pipeline status (see
`knowledge/playbooks/false-green-gates/README.md`). Never report a test as passed
unless it was executed. Before handing back, use the
[evidence-reconciliation procedure](../knowledge/playbooks/false-green-gates/README.md#reconcile-verification-claims)
to check summary claims against final results and saved files, including each
check's outcome and the scope of any preservation baseline. Inspect
`git diff --cached` before claiming changes are staged.
Don't apply fixes or change external state unless I've asked you to.

${ARGUMENTS:-}
