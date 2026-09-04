---
name: git-workflow-and-versioning
description: "Use when preparing a release, choosing a version bump, creating or moving tags, writing changelog or release-note content, or when git hygiene for shared history is in question: commits, branches, recovery, non-interactive continuation."
invocation: entry
---

# Git Workflow and Versioning

## Core Principle

Treat commits as verified save points with **communicative messages** - history
is for future readers (review, bisect, release). Shared refs are append-only.
Each repository has exactly one release authority.

## When to Use / NOT

- **Use when:** preparing a release; choosing which semver digit moves;
 creating, moving, or deleting tags; writing release notes or changelog
 entries; commit, branch, merge, or recovery hygiene for shared history.
- **NOT when:** GitHub repository settings or remote configuration
 (`github-repo-setup`); workflow files and release CI implementation
 (`github-actions-engineering`); the PR lifecycle itself (`push-pr`).

## Release strategy (adaptive; preserve what exists)

If the project already has a release process, preserve it. Otherwise pick one
authority and keep it:

1. **Tag + GitHub generated notes (default for GitHub-native projects).**
 Choose the version, push the `vX.Y.Z` tag, and let release CI verify the
 tree and publish with generated notes (categories driven by labels in
 `.github/release.yml`). No manual changelog to drift.
2. **Curated CHANGELOG.** When the project intentionally maintains one: move
 `[Unreleased]` to `[x.y.z] - date`, list `Deprecated` before `Removed`, tag
 after the changelog lands.
3. **Release automation (Release Please, semantic-release, ecosystem
 tooling).** Only when the project already runs one; never add a second
 authority beside an existing one.

Version class: breaking behavior change moves the major digit, new capability
the minor, a fix the patch; pre-releases use `x.y.z-rc.N` precedence. For
catalog and tooling repositories without a published API, bump by intent: a
change users must react to is at least minor.

## Process

1. **Worktree** - `git status --short`; never `git add .` in a mixed tree;
 stage by path.
2. **Branch** - short lowercase hyphenated name; project caps live in
 `AGENTS.md`.
3. **Commit unit** - one logical change; feature + tests together; `git add -p`
 to split.
4. **Message** - editor commit for non-trivial work: imperative subject
 (`type(scope): desc`), blank line, body ~72 cols with the **why**; run the
 repository's title or commit protocol when one exists.
5. **Before push** - gates pass; fixup/squash/rebase -i on private branches
 only; **never** force-push shared branches without explicit approval.
6. **Merge** - per project policy; `--no-ff` when branch topology matters.
7. **Release** - follow the project's release authority above; annotated tags
 unless the project chooses lightweight deliberately; read the release back
 after publishing.
8. **Evidence** - status, diff summary, gates run, version/tag/release action
 or explicit skip.

## Recovery & non-interactive continuation

- **Lost work or history:** `git reflog` -> identify the pre-damage commit ->
 restore additively (`git branch rescue <sha>`, cherry-pick, or a new commit
 of the recovered tree). Recover without destroying more history; reflog is a
 recovery mechanism, not a license for destructive operations.
- **Ceremonial editors:** when the message/content is already decided, suppress
 only the editor - `GIT_EDITOR=true git rebase --continue`,
 `GIT_SEQUENCE_EDITOR=true ...`, `git commit --no-edit`. Never override a
 prompt that represents a real decision (interactive-rebase TODO, conflict
 resolution choice, credential or confirmation prompt).
- **Generated or multi-line commit messages:** write to a securely created
 temporary file (`mktemp`) and commit with `git commit -F <file>` - never
 interpolate generated text into the command line. Short, simple subjects may
 pass as ordinary quoted arguments.

## Common Rationalizations

| Rationalization | Rebuttal |
|---|---|
| "I'll clean up the commit later." | Intent lost; rebase cost rises. |
| "git log is our changelog." | Users cannot scan merges and WIP; use the project's release authority (generated notes or a curated changelog). |
| "PATCH bump for a breaking change." | Destroys semver trust - MAJOR. |
| "Force-push main to fix." | Breaks the team - new forward commit instead. |

## Red Flags

- Subject with no blank line before body (breaks rebase/format-patch).
- Version tag does not match the published release notes (or the changelog
 header, when the project keeps one).
- Two release authorities running at once (tag + tool + manual changelog).
- `Deprecated` missing before `Removed` in a major release.
- Breaking change shipped as PATCH.
- Force-push of shared history without explicit approval.

## Verification

- `git status --short` and the diff/staged summary cited.
- `git log --format=%s origin/main..HEAD` matches the repository's documented commit convention when one applies.
- Release: the tag points at the intended commit; `gh release view` shows the
 published release with generated notes present.

## References

Prior-art capsules (optional reading, when the why matters):

- `awesome-guidelines/references/semver-public-api-and-bumps.md`
- `awesome-guidelines/references/semver-precedence-and-prerelease.md`
- `awesome-guidelines/references/git-style-branches.md`
- `awesome-guidelines/references/git-style-commit-messages.md`
- `awesome-guidelines/references/git-style-history-and-merge.md`
- `awesome-guidelines/references/changelog-style-learning-note.md`
