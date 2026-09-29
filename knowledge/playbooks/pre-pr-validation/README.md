---
title: pre-pr-validation
summary: 'Use when validating finished changes before a PR: select checks for the affected surface, verify behavior and dependencies, and review the diff. Track Sourcebot bot review separately after publication; push-pr owns delivery.'
kind: playbook
---

# Pre-PR validation

Produce a local readiness verdict and evidence for `../push-pr/README.md`.
This procedure does not authorize a push, PR, merge or tool installation.

## Establish scope

Identify the repository, target branch, merge base, HEAD and relevant staged,
unstaged and untracked changes. Preserve unrelated work. Define acceptance
checks and trace affected entrypoints, consumers, registrations and configuration.
Read project instructions and its PR template; select skills for the changed
surface rather than loading a general catalog.

## Select sufficient evidence

Cover the changed surface, not a fixed roster of tools. Local source reads,
compiler/linter checks, tests and focused behavioral probes are the default.
A missing optional integration does not block readiness. An unmet project gate,
explicitly required check or unresolved correctness finding does.

- **Behavior and project gates:** run relevant checks and direct probes. Inspect
  the verifier's exit status and decisive output, not only a pipeline filter's
  success (`../shell-scripting-practices/README.md`). A build alone does not prove
  behavior. Run `git diff --check` across the branch diff and local changes.
- **Source and dependency review:** trace affected callers and configuration in
  the working tree. Use a code graph, such as Fovea, when it helps resolve impact;
  do not require a graph pass for prose or metadata that direct inspection settles.
  For broad unresolved codebase questions where indexed coverage can help, or an
  explicit user request, use Sourcebot's `ask_codebase` through
  `../cross-repo-source/README.md`. Verify indexed findings against current source;
  neither an index nor a graph miss proves absence.
- **Diff quality:** review competing owners, unnecessary abstractions, speculative
  fallbacks, swallowed errors, vacuous tests, unrelated churn and unsupported
  claims. Run the project's artifact gate when present. Findings need a concrete
  path and consequence; presumed AI authorship and style preferences are not
  defects. Use `../code-cleanup/README.md` for justified simplification.
- **Optional IDE evidence:** use `../mcp-steroid/README.md` only when the project
  or user opts in and the task benefits from semantic navigation, refactoring,
  inspections or debugging. Enabling the server alone does not require an IDE
  check. Do not open an IDE or require a live-file witness for ordinary prose or
  configuration changes. If an explicitly required IDE check cannot run, report
  that gap; otherwise continue with sufficient local evidence.

## External patch review

[Sourcebot bot review](../sourcebot/references/review-workflow.md) is separate from
indexed research and local readiness. It requires a published PR: record PENDING
before publication or while fixes remain unpublished. Results cover only the
reviewed revision. Missing configuration, failures or unverifiable completion
are BLOCKED, not a clean review. Neither an Ask answer nor absence of comments
satisfies this gate. CodeRabbit remains an optional additional review.

`push-pr` owns authorized triggering, observation and feedback. Bot review blocks
merge when incomplete, not the authorized publication needed to obtain it.

## Resolve and hand off

Fix actionable findings and rerun affected checks. Reuse evidence only while its
base, HEAD, working-tree scope and acceptance requirements still match. PR metadata
edits do not invalidate unchanged code evidence; observe any resulting CI
through `push-pr`. For absence claims, confirm the search covers the relevant
roots and can find a known-present instance. Include inline path references,
not just Markdown links, when checking instruction consumers.

Use the existing task record or PR draft for one compact record:

- Scope: base/HEAD, local changes and acceptance checks.
- Evidence: commands/probes, exit status, covered paths and decisive output.
- Findings: location, consequence, disposition and remaining gaps.
- Optional tools: relevant observations or a material applicability/access limit;
  do not create a skipped-tool inventory.
- Verdict: local READY or BLOCKED; separately, Sourcebot bot PENDING, PASSED or
  BLOCKED with the reviewed revision and completion evidence when available.

Local READY means applicable checks passed and no local blocking finding remains.
It does not grant publishing permission or claim complete PR verification. An
explicitly requested draft/WIP may carry blockers, but is not READY. CI and the
completed patch review still gate merge. A no-PR request stops locally.

Update canonical documentation when contracts change; keep transcripts, secrets
and duplicate inventories out of Git.
