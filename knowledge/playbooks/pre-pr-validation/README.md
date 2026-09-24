---
title: pre-pr-validation
summary: 'Use when validating finished changes before pushing a PR: require project gates, CodeRabbit, IDE semantics, graph review, AI-slop rejection, and a revision-bound evidence record. push-pr owns remote delivery.'
kind: playbook
---

# Pre-PR validation

Validate the proposed change, not the agent's confidence. This phase produces a
local readiness verdict and evidence for `../push-pr/README.md`; it does not push,
create a PR, merge, or install tools.

## Establish scope

Identify the repository, target branch, merge base, HEAD, staged and unstaged
changes, and relevant untracked files. Preserve unrelated work. Record acceptance
checks and trace affected entrypoints, consumers, registrations and configuration
before judging implementation completeness. Read project instructions and its PR
template; project-required gates take precedence over generic shortcuts.

Select only skills relevant to the changed surface via
`../skill-catalog/README.md`: tests, security, frontend, native runtime, migration,
or CI as applicable. Read project documentation for those systems. Do not load
the whole catalog or copy its rules into a new checklist.

## Gather complementary evidence

Every PR must complete every quality lane below for every changed path, regardless
of diff size or file type. A missing tool, authorization, matching project,
unreported changed path, incomplete result, or required gate is a blocker, not an
`N/A` or silent skip. A draft/WIP may carry the blocker, but cannot receive a READY
verdict. Applicability is judged per lane: the Sourcebot baseline challenge applies
only when the change's correctness depends on indexed code evidence or the user
requested it, and its inapplicability is recorded with that reason instead of
forcibly calling the tool. The other lanes remain required as written.

- **Behavior and gates:** run project checks and focused behavioral probes;
  inspect command output and the verifier's own exit status. A pipeline can report
  the filter's success while hiding the verifier's error; use the status-handling
  procedure in `../shell-scripting-practices/README.md`.
  A build or graph trace alone does not prove behavior. Check whitespace across
  the branch diff and local changes, not only the unstaged diff.
- **Independent patch review:** run CodeRabbit through
  `../coderabbit-review/README.md` on the complete authored diff. Confirm the
  repository and external-upload authorization before submission, inspect command
  status, and triage every structured finding against source and tests.
- **IDE semantics:** call `steroid_list_projects` and route only to the project
  whose path matches the repository (`../mcp-steroid/README.md`). If none matches,
  immediately tell the user which repository to open in IntelliJ and keep the lane
  BLOCKED until relisting finds it. Inspect every changed path through the IDE; for
  code, inspect symbols, consumers and targeted diagnostics; for prose or
  configuration, use changed-file inspections and
  a live-file witness. Confirm index readiness where semantic APIs require it.
- **Graph and baseline review:** use the host's code-graph impact tool on the
  local working tree (`fovea_impact` under Pi) to trace affected callers and
  dependencies. Use Sourcebot's `ask_codebase` through
  `../cross-repo-source/README.md` to challenge the approach against the indexed
  baseline and comparable implementations when the change's correctness depends on
  code structure or callers, or when the user requested it; documentation- or
  design-only diffs record that applicability decision rather than forcing a call.
  Verify both against current source because an index or graph miss cannot prove
  absence.
- **AI-slop rejection:** run the project's objective artifact gate when present.
  Review the actual diff for competing owners, unnecessary abstractions,
  speculative fallbacks, swallowed errors, vacuous tests, unrelated churn and
  unsupported documentation claims. Findings need a concrete path and consequence;
  style preferences or presumed AI authorship are not defects. Use
  `../code-cleanup/README.md` for justified simplification, preserving behavior.

## Resolve and record

Fix actionable findings, then rerun affected checks. When a check asserts an absence
(no contradictory rule, no remaining call site, no stale reference), scope the pattern
so it cannot match the text you just introduced; observed 2026-09-17, a contradiction
grep matched the sentence written seconds earlier. Before reporting absence, also
confirm the check can see a known-present instance: a link-reachability sweep that
followed only markdown links reported gaps for instructions that reference their
target as an inline path (same day). New changes invalidate the
relevant earlier evidence; confirm the final revision and working-tree scope
before handoff. Reuse evidence only when its base, HEAD, working-tree scope and
acceptance requirements still match. A title/body-only PR edit does not itself
invalidate local evidence; a changed base, patch or requirement can. Revalidate
the record and rerun only affected checks. Remote CI triggered by metadata edits
still needs observation through `../push-pr/README.md`.

Use the existing task record or PR-body draft for one compact record:

- Scope: base/HEAD, local changes, acceptance checks and selected skills.
- Evidence: command/probe, scope, result/exit status and decisive output or link.
- Reviews: CodeRabbit status and finding dispositions; Steroid and Fovea
  observations; the Sourcebot baseline challenge where applicable, with the
  applicability reason or the access blocker; the AI-slop rejection outcome;
  source anchors, revisions, covered paths and limits.
- Findings: severity, location, resolution or remaining blocker.
- Context: why the change exists, decisions, relevant documentation updates.
- Verdict: READY or BLOCKED, with gaps and explicit exceptions.

Update canonical docs when behavior or contracts change; do not dump transcripts,
secrets, session state or a second architecture inventory into Git. Record durable
lessons only where they belong, using `../leverage-capture/README.md` when useful.

## Handoff

READY requires satisfied acceptance checks, an inspected result for every lane
above, and no unresolved blocking findings. Missing lane evidence means BLOCKED.
Hand the record to push-pr without implying permission to publish. An explicitly
requested draft/WIP push may carry a BLOCKED record, but never relabel it READY.
Remote CI and review remain separate delivery checks.
