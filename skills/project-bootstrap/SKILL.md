---
name: project-bootstrap
description: "Use when entering a new or unfamiliar repository, initializing a greenfield project workspace, or intentionally establishing lightweight persistent project-level agent context."
invocation: entry
---

# Project Bootstrap

Teach the agent how to enter the project, not document the universe. Default to
read-only understanding; persist only valuable, non-obvious context. Ordinary
work in a known repository stays in the normal development loop.

## Select from repository state and user intent

### A. Onboarding (read-only default)

Answer: what is this, how does it run/test/build, where are the main seams, and
what matters before editing? Inspect relevant instructions, README, manifests,
lockfiles, runtime files, entrypoints, CI, dirty state, generated/vendor boundaries,
and known traps. Use source first; graphs, history, or cold capability maps should
close a named gap, not become mandatory exploration.

If `reference/` or `reference/web/` exists, list top-level checkout/capture names
only. Do not ingest their contents during onboarding.

Return a compact **conversation summary**, not files: project/type/stack/runtime;
run/test/build commands with executed results; key paths, boundaries, current
state, traps, and reference asset names. An unexecuted command is not verified.
Do not create a roadmap, architecture encyclopedia, version cache, or user profile.

### B. Govern (persistent context requested)

Inspect existing instructions before adding anything. Use
`../../templates/agents.md` for missing, valuable local instructions: verified
commands, non-obvious invariants, traps, and enforced conventions. Optionally
create one 30–60-line context file from `../../templates/project-context.md` at
`docs/project-context.md` or the native location. Record expensive-to-reconstruct
intent and unsupported behavior, not a manifest cache. Use
`../../templates/roadmap.md` only for an explicitly requested roadmap.

Delegate requested GitHub governance to `../github-repo-setup/SKILL.md` and CI to
`../github-actions-engineering/SKILL.md`; neither is an automatic side effect.

### C. Greenfield

Skip deep existing-repo detection in an empty directory. Unclear direction goes
to `../brainstorming/SKILL.md`; clear direction goes to native stack scaffolding.
"Start a new project" alone does not request GitHub or CI setup: report what was
skipped. Requests for "our baseline", "standard setup", "production-ready",
"OSS-ready", or "full setup" authorize the baseline after scaffolding: GitHub
setup at the maturity class in
`../github-repo-setup/references/setup-matrix.md`, then CI, then
`../git-workflow-and-versioning/SKILL.md` only for a versioned project.

Start complex/high-risk creation from user constraints too. When durable recovery
or coordination state may be needed, explicitly load `../goal-setup/SKILL.md`;
it owns qualification, not a duration threshold.

### D. Refresh

Inspect, compare, and update only stale guidance. Preserve handwritten decisions
and intentional local instructions; never rebuild from scratch. A second run on
a current repository reports "nothing to change".

## Verify and stop

If setup or refresh verification fails, do not claim completion: reopen the
evidence, record the reproducible failure and its root cause, and load
`../debugging-and-error-recovery/SKILL.md` before retrying or reporting.

Onboarding writes no files. For persistent changes, confirm files exist, reconcile
with prior content, and contain verified or `[NEEDS CLARIFICATION]` claims. Never
record a failing command as a working Verify command. Refresh changes only the
identified stale set.

Do not persist machine-recoverable versions, branches, dependency lists, or dirty
state. Do not create personal-preference files or default host artifact packs
(such as `.pi/project.md`/`.pi/state.md`); host runtime state belongs in host
configuration or explicitly requested project governance.
