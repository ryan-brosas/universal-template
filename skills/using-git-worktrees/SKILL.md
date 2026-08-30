---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git worktrees with smart directory selection and safety verification
---


# Git Worktrees

## Core Principle

Isolation without duplication: a worktree is a separate working directory for the same git repo — its own branch, shared `.git`, cheap to create, instant to switch between.

## When to Use

Starting a feature that needs isolation from current workspace; multi-agent work in same repo; long-running branch that doesn't conflict with main; need to test a PR without disrupting the working copy; switching between contexts without `git stash`; running CI / tests in parallel.

## When NOT to Use

Trivial change on main; one-line fix; the branch is already on a worktree; you need to commit and move on quickly.

## Workflow

1. Run the safety checks first: `git worktree list` (is the branch already on a worktree?), `git status` (commit or stash if dirty), target directory empty, absolute path (Safety Checks).
2. Create with a sibling directory, not nested: `git worktree add -b <branch> ../myapp-<branch> main` (Create a Worktree, Smart Directory Selection).
3. Do the work in the worktree; commit before switching contexts.
4. Clean up when done: `git worktree remove ../X && git worktree prune` (Common Patterns).

## What a Worktree Is

A worktree is a separate working directory for the same git repo. Each has its own branch, but they share the `.git` directory. Cheap to create, instant to switch between.

```
~/code/myapp          ← main worktree, on `main`
~/code/myapp-feature  ← worktree, on `feature/auth`
```

Both share history. Both can be on different branches. Both are full working copies.

## Create a Worktree

```bash
# New branch + new worktree
git worktree add -b feature/auth ~/code/myapp-feature main

# Existing branch
git worktree add ~/code/myapp-feature feature/auth

# PR (just the work, not the branch)
git worktree add --detach ~/code/myapp-pr origin/pr/123
```

`add -b` creates a new branch. Without, the existing branch is checked out.

## Common Patterns

| Pattern                | Command                                             |
|------------------------|-----------------------------------------------------|
| Feature work, isolated | `git worktree add -b feature/X ../X main`           |
| Switch back to main    | `cd ../myapp && git checkout main`                  |
| Compare two branches   | Two worktrees, diff between them                    |
| Review a PR            | `git worktree add --detach ../pr-123 origin/pr/123` |
| Cleanup old            | `git worktree remove ../X && git worktree prune`    |

## Smart Directory Selection

```
~/code/myapp          ← existing
~/code/myapp-feature  ← new, sibling
```

Use a sibling directory, not nested. Avoids confusion with `pwd`.

```bash
# Inside myapp/, create sibling myapp-<branch>
git worktree add -b $BRANCH ../myapp-$BRANCH main
```

## Safety Checks

Before creating a worktree:
- **Is the branch already on a worktree?** `git worktree list` shows all.
- **Is the working copy dirty?** `git status` — commit or stash first.
- **Is the target directory empty?** Don't overwrite.
- **Is the path absolute?** `git worktree add` requires absolute paths in some configs.

## Common Mistakes

Creating a worktree inside the repo (nested paths confuse `pwd`); trying to check out the same branch in two worktrees (refused); leaving dead worktrees around (prune them); pushing to the wrong branch (you have two now); not committing before switching (lost work, not in stash); "I created a worktree for a 5-line fix" (overhead); forgetting which directory you're in (the worktree problem).

## Red Flags

Worktree inside the repo; same branch in two worktrees; dead worktrees not pruned; "I lost my changes" (didn't commit before switching); "which directory am I in?"; pushing to wrong branch; "I have 5 worktrees" (prune, focus); worktree for one-line fix.

## Anti-Patterns

**Nested worktrees** (sibling); **same branch twice**; **dead worktrees** (prune); **uncommitted switch** (lost work); **"which dir"** (single-purpose worktree, finish or prune); **worktree for one-liner**; **5 worktrees** (focus, prune).

## Verification

- `git worktree list` shows the new worktree on the intended branch; `pwd` confirms you are in the sibling directory, not nested inside the repo.
- `git status` is clean in both copies before any switch; no uncommitted work remains in a worktree before removal (Safety Checks, Common Mistakes).

## Skill Result Contract

```
<skill_result>
  <skill><name></skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References

N/A — no references/ directory; the skill is a self-contained prompt corpus.
