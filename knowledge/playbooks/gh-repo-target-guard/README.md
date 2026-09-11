---
title: gh-repo-target-guard
summary: Use before creating or updating a GitHub PR with gh in any checkout that has an upstream remote (fork setups), when a gh command runs without an explicit --repo flag, when a just-created PR's URL or PR number looks wrong for the intended repository, or when GitHub reports a PR CONFLICTING although the local merge graph proves a clean fast-forward. Verifies gh's resolved repository against git remotes before any GitHub write, and diagnoses PRs opened against the wrong repository.
kind: playbook
---

# gh repo target guard

gh does not target repositories from git remotes. Every gh command in a checkout
resolves the repository from its own default selection
(`gh repo set-default --view`), which is independent of `git remote -v`. When
that default points at upstream while origin is a fork (or vice versa),
`gh pr create` without `--repo` opens the PR against the wrong repository,
possibly as a cross-fork PR whose base branch history differs from the local
base.

## Intent rule: the fork is the default target

This failure recurs even when every check below is followed: an agent reasons
from a stated long-term goal ("contribute this work upstream someday") and
opens the PR on upstream with an explicit `--repo` — mechanically correct,
wrong intent. The rules:

- A bare "commit, push and PR" / "ship it" request targets the fork
  (`origin`).
- The existence of an `upstream` remote is not permission, and passing
  `--repo <upstream>` explicitly is not authorization: only a current,
  explicit user instruction to open an upstream PR is.
- A long-term contribution goal stated in plans, roadmaps, or past
  conversation is not a per-request instruction.
- Repository guidance (AGENTS.md) declaring fork-only pushes/PRs is
  authoritative; a disabled `upstream` push URL confirms that contract.

## Check before any gh write

1. `git remote -v`: note `origin` and any `upstream`. For fork-local work the
   PR base is `origin`; confirm explicitly when an upstream PR is actually
   wanted.
2. `gh repo set-default --view`: the repository gh will use without `--repo`.
3. When they disagree, or an upstream remote exists at all, pass the target
   explicitly: `gh pr create --repo <owner>/<repo> --head <branch>` (the head
   repo too, when it differs from the base repo). Never rely on the default in
   a fork checkout.
4. Make the intent durable: `gh repo set-default <owner>/<repo>` matching the
   intended base for this checkout, then re-verify.
5. After creation, verify: the PR URL is on the intended repository and the PR
   number fits that repository's merge history.

Read-only gh commands follow the same default: in a mismatched checkout
`gh pr view`/`gh pr checks` silently inspect the wrong repository's PRs.

## Diagnosis signatures

- Wrong-repo PR: the URL's repository is not `origin`, head and base live in
  different repositories, or the PR number is inconsistent with the origin
  repository's history. Fix: close with an explanatory comment and recreate
  with explicit `--repo`/`--head`. GitHub cannot move a PR between
  repositories.
- `mergeable: CONFLICTING`/`DIRTY` while `git merge-base HEAD <base>` equals
  the base tip and `git log <base> ^HEAD` is empty: the local graph proves a
  fast-forward, so the PR's base repository differs from the local base. Check
  repository identity before touching the branch; do not rebase or rewrite a
  clean history to chase a phantom conflict.

## Boundaries

Close-and-recreate is the only fix for a wrong-repo PR; never force-push or
rebase to work around a repository-identity mismatch. Do not change
`gh repo set-default` in a checkout the user shares for upstream contributions
without stating the new default.
