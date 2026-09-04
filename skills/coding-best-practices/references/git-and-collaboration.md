# Git and collaboration

## Every project uses version control

- Commit at natural checkpoints with a coherent, verifiable diff (`code-discipline`).
- Do not leave work uncommitted at end of turn unless the user asked.

## Branches

- Short-lived feature branches off the project base (`main` unless AGENTS.md says otherwise).
- Branch names: lowercase, hyphen-separated, ≤3 segments (global convention in `AGENTS.md`).

## Commits

- Subject: follow the project convention; when it uses conventional titles, prefer `type(scope): summary`.
- Imperative mood, no trailing period, no leading capital in description segment.
- Body explains **why** when the subject is not enough.

## Pull requests

- Fill the body from `~/.agents/templates/pull-request.md` via `push-pr`.
- Work is not done at push — CI green and review comments resolved (`code-discipline`).
- Set labels/metadata at `gh pr create` time; watch the workflow run to completion.

## Conflicts and history

- Rebase or merge per team policy; never force-push shared branches without explicit request.
- Resolve conflicts in the files you touched; run the project gate after resolution.

## Mechanical gates

- `git diff --check` (whitespace)
- Direct `git log --format=%s` review against the project convention
- The project's PR quality workflow
- PR title check (`pr-title.yml` on catalog)

## Leaf skills

- `git-workflow-and-versioning` — application skill (deep Git/semver/changelog learning)
- `awesome-guidelines/references/git-style-learning-note.md` — why behind branch/commit/merge rules
- `push-pr`, `github-actions-engineering`, `code-discipline`, `code-review-and-quality`
