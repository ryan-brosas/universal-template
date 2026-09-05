---
name: project-bootstrap
description: "Use when entering a new or unfamiliar repository, initializing a greenfield project workspace, or intentionally establishing lightweight persistent project-level agent context."
invocation: entry
---

# Enter a project

Orient just enough to do the requested work. For an existing repository, local
instructions, dirty state, entrypoints, manifests, tests and CI usually answer
what it is, where to change it and how to verify. A complete inventory or an
onboarding report is not a prerequisite for implementation. Distinguish commands
found in source from commands actually run; do not run every build merely to
learn the repository.

If `reference/` or `reference/web/` exists, a top-level listing can reveal useful
prior art without ingesting it. Reach for graph tools or the cold
`../skill-catalog/SKILL.md` discovery path only when they close a knowledge gap.

## Persistent setup, when requested

Reconcile existing instructions rather than replacing them. Use
`../../templates/agents.md` for non-obvious project invariants, traps and useful
verification commands. Run a command before recommending it as a verified gate.
A separate context file (`../../templates/project-context.md`) earns its place
only for durable intent or decisions expensive to recover from source. Do not
create a default host-state pack, roadmap, personal profile or manifest cache.
Runtime state belongs to the host; personal data does not belong in project Git.

For a greenfield project, clarify only unresolved requirements, then scaffold
with the stack's native tooling. GitHub, CI and release setup are separate scope:

- A scratch/local project does not authorize remote setup.
- An explicitly requested standard or production/OSS baseline can use
  `../github-repo-setup/SKILL.md` and `../github-actions-engineering/SKILL.md`.
  Preserve the user's choices of ownership, visibility and license.
- Unclear product direction may benefit from `../brainstorming/SKILL.md`; a
  durable recovery or coordination need may benefit from `../goal-setup/SKILL.md`.
  Neither is an automatic phase.

Finish the requested task, or give a short orientation if that was the task.
Report actual checks and unresolved setup gaps without creating work records
merely to prove onboarding happened.

If setup or refresh fails, diagnose the failure before retrying or claiming
completion; `../debugging-and-error-recovery/SKILL.md` can help.
