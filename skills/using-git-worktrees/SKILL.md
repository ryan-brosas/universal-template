---
name: using-git-worktrees
description: "Use when parallel or conflicting work in the same repo needs a separate checkout without stashing — sibling worktree; verify the branch is not already checked out elsewhere."
invocation: manual
disable-model-invocation: true
---

# Git worktrees (isolation)

## Core Principle

Isolation without duplicating history: a sibling worktree shares `.git` but keeps
its own working tree and branch.

## When to Use / NOT

- **Use when:** parallel work in one repo, a long-running branch beside main, or
  PR review without disturbing a dirty working tree.
- **NOT when:** one-line fixes on main.

## Workflow

1. `git worktree list` — target branch not already on another worktree.
2. `git status` — commit or stash unrelated dirty state first.
3. `git worktree add -b <branch> ../<repo>-<branch> main` — sibling directory,
   not nested inside the repo.
4. Work and commit in the worktree; remove when done:
   `git worktree remove ../<repo>-<branch> && git worktree prune`.

## Verification

`git worktree list` shows the new path on the intended branch; `pwd` is the
sibling directory, not nested inside the repo.
