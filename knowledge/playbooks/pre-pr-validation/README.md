---
title: pre-pr-validation
summary: 'Use when validating finished changes before pushing a PR: coordinate project gates, semantic and graph review, AI-slop rejection, and a revision-bound evidence record. push-pr owns remote delivery.'
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

- **Behavior and gates:** use `../agent-code-quality-gate/README.md`. Run project
  checks and focused behavioral probes; inspect command output and exit status.
  A build or graph trace alone does not prove behavior. Check whitespace across
  the branch diff and local changes, not only the unstaged diff.
- **IDE semantics:** for nontrivial symbol/API changes, discover available IDE
  tools and use `../mcp-steroid/README.md`. Confirm the correct project and ready
  index, inspect changed symbols and consumers, and review targeted diagnostics.
  Do not silently apply broad quick-fixes or treat inspections as tests.
- **Graph review:** use the active working-set graph when available. For an
  existing Codebase Memory index, load `../codebase-memory/README.md`, confirm
  repository/revision and coverage, then trace affected callers and dependencies.
  Confirm findings in current source. A stale or partial index cannot prove
  absence of callers. Do not create, rebuild or delete indexes without the
  authorization required by that skill. Use source search and tests as fallback.
- **AI-slop rejection:** run the project's objective artifact gate when present.
  Review the actual diff for competing owners, unnecessary abstractions,
  speculative fallbacks, swallowed errors, vacuous tests, unrelated churn and
  unsupported documentation claims. Findings need a concrete path and consequence;
  style preferences or presumed AI authorship are not defects. Use
  `../code-cleanup/README.md` for justified simplification, preserving behavior.

Unavailable optional tools are reported with the reason and substitute evidence,
never as passes. If the project requires that capability or the substitute leaves
an acceptance condition unproved, readiness is blocked.

## Resolve and record

Fix actionable findings, then rerun affected checks. New changes invalidate the
relevant earlier evidence; confirm the final revision and working-tree scope
before handoff. Do not rerun unchanged passing checks without a reason.

Use the existing task record or PR-body draft for one compact record:

- Scope: base/HEAD, local changes, acceptance checks and selected skills.
- Evidence: command/probe, scope, result/exit status and decisive output or link.
- Semantics: IDE/graph observations, source anchors, coverage and fallback limits.
- Findings: severity, location, resolution or remaining blocker.
- Context: why the change exists, decisions, relevant documentation updates.
- Verdict: READY or BLOCKED, with gaps and explicit exceptions.

Update canonical docs when behavior or contracts change; do not dump transcripts,
secrets, session state or a second architecture inventory into Git. Record durable
lessons only where they belong, using `../leverage-capture/README.md` when useful.

## Handoff

READY requires satisfied acceptance checks, inspected required-gate successes and
no unresolved blocking findings. Missing required evidence means BLOCKED.
Hand the record to push-pr without implying permission to publish. An explicitly
requested draft/WIP push may carry a BLOCKED record, but never relabel it READY.
Remote CI and review remain separate delivery checks.
