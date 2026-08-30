---
name: git-workflow-and-versioning
description: "Use when making code changes that need safe git hygiene, atomic commits, branch strategy, versioning, changelog entries, or release preparation - trunk-based development, commit-as-save-point discipline."
disable-model-invocation: true
---


# Git Workflow and Versioning

Application skill for Git + semver + changelog learning (`awesome-guidelines` deep ingest). Read learning notes when reasoning about *why*; use capsules for probes.

## Core Principle

Treat commits as verified save points with **communicative messages** — history is for future readers (review, bisect, release). Shared refs are append-only; semver + changelog are the user-facing contract.

## When to Use

- Commits, branches, merges, tags, releases, or changelog updates.
- Dirty worktree with unrelated user changes.
- Version bump decisions (which semver digit).

## When NOT to Use

- Read-only investigation with no VCS mutations planned.

## Process

1. **Worktree** — `git status --short`; never `git add .` in a mixed tree; stage by path.
2. **Branch** — name per `awesome-guidelines/references/git-style-branches.md` (short, lowercase, hyphens; project cap in `AGENTS.md`).
3. **Commit unit** — one logical change; feature + tests together; `git add -p` to split (`git-style-commit-messages.md`).
4. **Message** — editor commit for non-trivial work: subject (imperative ~50 chars or conventional `type(scope):`), blank line, body ~72 cols with **why**; run `conventional-commit.py` when catalog applies.
5. **Before push** — tests pass; history on private branch may use fixup/squash/rebase -i; **never** force-push shared branches without explicit approval (`git-style-history-and-merge.md`).
6. **Merge** — rebase or merge per project; `--no-ff` when policy preserves branch topology.
7. **Release** — classify change against public API (`semver-public-api-and-bumps.md`); bump manifest; move `[Unreleased]` → `[x.y.z] - ISO-date` in CHANGELOG (`changelog-human-curation.md`); annotated tag; pre-release precedence if applicable (`semver-precedence-and-prerelease.md`).
8. **Evidence** — status, diff summary, gates run, version/changelog/tag action or explicit skip.

## Recovery & non-interactive continuation

- **Lost work or history:** `git reflog` → identify the pre-damage commit → restore additively (`git branch rescue <sha>`, cherry-pick, or a new commit of the recovered tree). Recover without destroying more history; reflog is a recovery mechanism, not a license for destructive operations.
- **Ceremonial editors:** when the message/content is already decided, suppress only the editor — `GIT_EDITOR=true git rebase --continue`, `GIT_SEQUENCE_EDITOR=true …`, `git commit --no-edit`. Never override a prompt that represents a real decision (interactive-rebase TODO, conflict resolution choice, credential or confirmation prompt).
- **Generated or multi-line commit messages:** write to a securely created temporary file (`mktemp`) and commit with `git commit -F <file>` — never interpolate generated text into the command line. Short, simple subjects may pass as ordinary quoted arguments.

## Common Rationalizations

| Rationalization | Rebuttal |
|---|---|
| "I'll clean up the commit later." | Intent lost; rebase cost rises. |
| "git log is our changelog." | Users can't scan merges/WIP — curate CHANGELOG. |
| "PATCH bump for breaking API." | Destroys semver trust — MAJOR. |
| "Force-push main to fix." | Breaks team — new forward commit instead. |

## Red Flags

- Subject with no blank line before body (breaks rebase/format-patch).
- Version tag ≠ manifest ≠ CHANGELOG header.
- `Deprecated` missing before `Removed` in major release.
- Breaking change shipped as PATCH.

## Verification

- `git status --short` and diff/staged summary cited.
- `CHECK_RANGE=origin/main..HEAD python3 scripts/conventional-commit.py` when on catalog branch.
- Release: semver bump matches change class; CHANGELOG section exists for version; tag name documented.

## Skill Result Contract

```xml
<skill_result>
  <skill>git-workflow-and-versioning</skill>
  <status>completed|blocked|skipped</status>
  <artifacts>Branch, commits, CHANGELOG, version file, tag, or none</artifacts>
  <evidence>git status/diff, conventional-commit, changelog/version alignment</evidence>
  <risks>history rewrite on shared branch, semver mismatch, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/git-style-learning-note.md`
- `awesome-guidelines/references/semver-learning-note.md`
- `awesome-guidelines/references/changelog-style-learning-note.md`
- `awesome-guidelines/references/git-style-branches.md`
- `awesome-guidelines/references/git-style-commit-messages.md`
- `awesome-guidelines/references/git-style-history-and-merge.md`
- `awesome-guidelines/references/semver-public-api-and-bumps.md`
- `awesome-guidelines/references/semver-precedence-and-prerelease.md`
- `awesome-guidelines/references/changelog-human-curation.md`
