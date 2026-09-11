---
title: git-workflow-and-versioning
summary: 'Use when preparing a release, choosing a version bump, creating or moving tags, writing changelog or release-note content, or when git hygiene for shared history is in question: commits, branches, base comparison and stale-base rebases, divergence and squash-merge reconciliation, post-merge branch state, recovery, non-interactive continuation.'
kind: playbook
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
 tree and publish with generated notes. Add a `.github/release.yml` only when the
 project wants label-driven categories; without one, GitHub applies its default
 taxonomy. No manual changelog to drift.
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

1. **Worktree** - re-read `git status --short` immediately before staging;
 stage only owned paths (or owned hunks in shared files), never `git add .` or
 `git add -A` in a mixed tree. Read `git diff --cached` itself, not only its
 `--stat`: a whole-file diff of a shared file also picks up lines another writer
 added to it since your last read. An unexpected path or hunk is a stop signal,
 not something to audit after pushing. Unstage unrelated changes without
 changing their working-tree content.
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
 or explicit skip. Before reporting, read the branch and publish state you
 actually observe (`git status -sb`, `git rev-parse --abbrev-ref HEAD`,
 `git branch -r --contains <sha>`): a shared worktree can be switched, or your
 uncommitted edits committed, by another writer between the edit and the report. A
 concurrent writer holding a stale copy can also revert a change you just pushed when
 they save their file: re-read the file and your own commit before reading intent into
 the revert, then re-apply without discarding their newer lines.

## Recovery & non-interactive continuation

- **Lost work or history:** `git reflog` -> identify the pre-damage commit ->
 restore additively (`git branch rescue <sha>`, cherry-pick, or a new commit
 of the recovered tree). Recover without destroying more history; reflog is a
 recovery mechanism, not a license for destructive operations.
- **Never discard work you did not write.** `git reset --hard`,
 `git checkout -- <path>` and `git restore <path>` destroy another writer's
 unsaved edits in a shared tree, and the loss is silent. `git reset --keep
 <sha>` keeps uncommitted changes and aborts when one would be overwritten, but
 it is not a no-op: clean files still move with HEAD. To read another revision
 without disturbing the tree at all, use `git worktree add` or
 `git show <sha>:<path>`. When only your own paths need to be clean, commit or
 stash those paths by name instead of resetting the tree.
- **A discarded edit is often recoverable.** Content can survive as a dangling
 object after a reset, stash drop or history rewrite. Check `git reflog`,
 `git fsck --lost-found`, and any commit that staged the path
 (`git show <sha>:<path>`), then restore it into the file additively and
 confirm the resulting diff is exactly the change that was lost.
- **Ceremonial editors:** when the message/content is already decided, suppress
 only the editor - `GIT_EDITOR=true git rebase --continue`,
 `GIT_SEQUENCE_EDITOR=true ...`, `git commit --no-edit`. Never override a
 prompt that represents a real decision (interactive-rebase TODO, conflict
 resolution choice, credential or confirmation prompt).
- **Generated or multi-line commit messages:** write to a securely created
 temporary file (`mktemp`) and commit with `git commit -F <file>` - never
 interpolate generated text into the command line. Short, simple subjects may
 pass as ordinary quoted arguments.

## Reconciling a branch with squash-merged upstream

A squash merge creates new commit SHAs, so a local branch "ahead" of upstream
may contain no work upstream lacks. Reconcile by content before rebasing:

1. Compare content, not counts: `git diff origin/main <branch> --stat` and
   `git log --oneline origin/main..<branch>`.
2. Treat a local commit whose change already exists upstream (typically
   refined) as stale, not extra. During rebase, git may drop it with "patch
   contents already upstream" - expected, not data loss.
3. Resolve superseded conflicts by taking upstream: during a rebase onto
   upstream, `git checkout --ours` is the upstream side; afterwards continue
   with `GIT_EDITOR=true git rebase --continue`.
4. Keep staging by path through conflict resolution (Process 1); a bare
   `git add -A` sweeps unrelated untracked scratch into the rebased commit.
5. Verify the residual diff (`git diff origin/main <branch> --stat`) contains
   only intended work, and run affected tests from the directory their runner
   expects.

## Comparing a branch with its base

Two comparisons answer different questions; do not substitute one for the other:

- `git diff <base>...HEAD` (three-dot, measured from the merge base) is what the PR
  shows and what a merge preserves: only the branch's own changes. Use it for pre-PR
  review, `git diff --check`, and gate ranges.
- `git diff <base>..HEAD` (two-dot, tip to tip) compares the two trees directly. It
  reports everything the base gained while the branch was open as deletions, so a stale
  base looks like a regression the merge would never cause - but it is the correct
  comparison when the question is whether the trees differ, as when deciding whether a
  squash-merged change is already upstream (see above).

Test drift directly with `git merge-base --is-ancestor <base-tip> HEAD`. A stale base
is a conflict-hygiene reason to rebase, not evidence that the merge discards base work:
keep the base's newer content, and rebase only when the same files are touched.

After a merge, fetch the branch before concluding that nothing else landed on it. A
concurrent session can push to a merged branch, leaving commits no PR covers
(`git fetch origin <branch> && git log --oneline <merged-head>..FETCH_HEAD`), and a
stale remote-tracking ref makes that log look empty.

## Common Rationalizations

| Rationalization | Rebuttal |
|---|---|
| "I'll clean up the commit later." | Intent lost; rebase cost rises. |
| "git log is our changelog." | Users cannot scan merges and WIP; use the project's release authority (generated notes or a curated changelog). |
| "PATCH bump for a breaking change." | Destroys semver trust - MAJOR. |
| "Force-push main to fix." | Breaks the team - new forward commit instead. |
| "Our branch is ahead, so it has unique work." | Squash merges rewrite SHAs; compare content before assuming. |

## Red Flags

- Subject with no blank line before body (breaks rebase/format-patch).
- Version tag does not match the published release notes (or the changelog
 header, when the project keeps one).
- Two release authorities running at once (tag + tool + manual changelog).
- `Deprecated` missing before `Removed` in a major release.
- Breaking change shipped as PATCH.
- Force-push of shared history without explicit approval.
- Rebasing a diverged branch without checking whether upstream already contains the work.

## Verification

- `git status --short` and the diff/staged summary cited.
- `git log --format=%s origin/main..HEAD` matches the repository's documented commit convention when one applies.
- Release: the tag points at the intended commit; `gh release view` shows the
 published release with generated notes present.
