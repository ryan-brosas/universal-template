---
title: project-bootstrap
summary: Use when the user asks to initialize or scaffold a project, refresh project-level agent context, or get repository orientation. Not for ordinary tasks in an unfamiliar repository.
kind: playbook
---

# Enter a project

This playbook owns requested setup or orientation, not routine context gathering.
For ordinary work, inspect only what the task needs. The optional
`../../../prompts/init-project.md` prompt enters this playbook; no extension or
special command is required.

## Ground and route

Inspect existing instructions, relevant source, manifests, tests and documentation,
and the user's stated goals before asking questions. Distinguish commands found
from checks actually run; do not run every build merely to learn the repository.
For greenfield work, ground in the user's brief rather than inventing architecture.

A missing context file does not mean missing understanding. Route by unresolved
substance, loading only the selected playbook and its needed references:

- Purpose, audience, desired outcome or direction is unclear: use
  `../brainstorming/README.md` to settle the load-bearing decisions.
- A direction is stated but its consequential assumptions are unexamined — an
  irreversible step with no rollback, a "nothing else depends on this" claim,
  asserted consensus, or a deferred scale or security concern: use
  `../grill-me/README.md` before writing setup output. Ground questions in
  available evidence; stop when the necessary uncertainty is resolved, not after
  a fixed number of questions. Route to it even when no user is available to
  answer: report the exact open questions instead of treating silence as
  agreement, and do not let a setup request itself push you past this branch.
- The repository and user already provide sufficient context: proceed directly,
  even if no context file exists. Do not force brainstorming or grilling.

Do not automatically chain both conversations. Ask only what existing evidence
cannot answer. Return to setup when decisions are sufficient; if blocked, name
what remains undecided rather than fabricating context or scaffolding around it.

If `reference/` or `reference/web/` exists, a top-level listing can reveal prior art
without ingesting it. Use graph tools or `../skill-catalog/README.md` only to close
a real knowledge gap, not to build a complete inventory.

## Persistent setup, when requested

Keep ownership separate:

- The user's global `AGENTS.md` owns standing engineering and safety rules.
- Project `AGENTS.md` adds repository invariants, verified checks, traps and
  operational boundaries using `../../../templates/agents.md`. It does not grant
  exceptions to global rules; surface conflicts for clarification.
- Durable project context records purpose, audience, scope/non-goals, constraints
  and agreed decisions using `../../../templates/project-context.md`. Prefer an
  existing document; create a separate file only when requested or when the
  information is useful and expensive to recover. Link it rather than duplicate it.

Reconcile existing instructions and handwritten context rather than replacing
them. Preserve supported decisions; clarify conflicting or stale claims before
changing their meaning. Mark unresolved facts explicitly. Do not fill templates
with placeholders merely to complete sections. Run a command before calling it a
verified gate; report unavailable checks honestly.

Orientation alone does not authorize new files. Do not create a default roadmap,
host-state pack, personal profile, manifest cache or separate grilling report.
Runtime state belongs to the host; personal data does not belong in project Git.
A concrete recovery or coordination need can use `../goal-setup/README.md`.

For requested greenfield scaffolding, settle necessary requirements first and use
the stack's native tooling. Context setup alone does not authorize implementation.
GitHub, CI and release setup are separate scope:

- A scratch/local project does not authorize remote setup.
- An explicitly requested standard or production/OSS baseline can use
  `../github-repo-setup/README.md` and `../github-actions-engineering/README.md`.
  Preserve the user's choices of ownership, visibility and license.

## Finish

Report what was established, actual checks, and unresolved decisions or setup
gaps. Do not create work records merely to prove onboarding happened. If setup or
refresh fails, diagnose before retrying or claiming completion;
`../debugging-and-error-recovery/README.md` can help.
