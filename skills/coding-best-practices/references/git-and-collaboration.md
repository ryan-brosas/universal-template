# Git and collaboration

## Checkpoints and commits

- Commit at a natural, verifiable checkpoint when the user or project workflow
  requests a commit.
- Follow the project's branch and commit conventions; do not impose a global
  branch shape or prose style.
- Explain why in the body when the subject does not make the reason clear.

## Pull requests

- Use the project's PR template and the applicable delivery skill.
- When the requested delivery includes a PR, inspect required CI and unresolved
  review comments before calling it complete.
- Apply labels or metadata through the repository's supported automation.

## Conflicts and history

- Rebase or merge according to team policy. Never force-push shared history
  without explicit authorization.
- Resolve conflicts within the requested scope, preserve unrelated user work,
  and rerun affected gates.

## Useful checks

- `git diff --check`
- direct review of `git diff` and `git log --format=%s`
- the project's required PR checks

## Leaf skills

- `git-workflow-and-versioning`, deep Git, versioning, and changelog guidance
- `push-pr`, bounded PR creation and update workflow
- `ship-pr`, explicitly requested end-to-end delivery
- `github-actions-engineering`, CI workflow ownership
