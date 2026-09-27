---
title: gh-repo-target-guard
summary: Use before creating or updating a GitHub PR with gh in any checkout that has an upstream remote (fork setups), when a gh command runs without an explicit --repo flag, when a just-created PR's URL or PR number looks wrong for the intended repository, or when GitHub reports a PR CONFLICTING although the local merge graph proves a clean fast-forward. Verifies gh's resolved repository against git remotes before any GitHub write, and diagnoses PRs opened against the wrong repository.
kind: playbook
---

# gh repo target guard

Repository selection depends on the command, explicit arguments/`--repo`,
`GH_REPO`, and checkout context (including git remotes and any configured gh
default). `origin` alone does not prove the target. `gh repo set-default --view`
shows a configured default, not every override or the effective target of every
command; it can report no default even when other commands infer a repository.
The [manual](https://cli.github.com/manual/gh_repo_set-default) also excludes
repository/environment secrets from this default. Pass explicit targets rather
than treating one default as a universal safety gate.

For auth, environment and API mechanics, use
[GitHub CLI](../github-cli/README.md).

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
2. Inspect `GH_REPO`/`GH_HOST` and `gh repo set-default --view` alongside the
   remotes. For a command relying on checkout inference, `gh repo view --json
   nameWithOwner,url` checks repository identity; do not confuse a missing
   configured default with missing repository access.
3. Pass the intended target explicitly on reads and writes where supported:
   `gh pr create --repo <owner>/<repo> --head <branch>` (use `<user>:<branch>`
   when the head is in a different user-owned fork). `--head` skips gh's automatic
   push/fork behavior; push separately only when authorized. Check installed help
   for organization-owned head limitations rather than guessing.
4. A persistent default is optional, not a repair prerequisite. If changing it
   is wanted, state the checkout-local effect, run
   `gh repo set-default <owner>/<repo>`, and re-verify. Do not silently change a
   shared checkout's default merely to make an explicit-target command work.
5. After creation, verify the PR URL and actual base/head repository and branch
   identities against the intended operation; a PR number alone proves nothing.

Read-only commands need the same explicit target: a mismatched
`gh pr view`/`gh pr checks` result can describe another repository's PRs.

## Diagnosis signatures

- Wrong-repo PR: the URL/base repository differs from the intended target.
  Different head and base repositories are normal for an authorized upstream
  contribution, not proof of an error. GitHub cannot move a PR between
  repositories; with approval to close the mistaken PR, explain and recreate it
  with explicit `--repo`/`--head`.
- `mergeable: CONFLICTING`/`DIRTY` while the local graph proves a fast-forward:
  first compare the remote PR's base/head repositories and SHAs with freshly
  fetched refs. A target mismatch, stale local refs or asynchronous mergeability
  can explain the discrepancy; the local graph alone does not prove which.
  Do not rewrite history to chase an unverified conflict.

## Boundaries

Close-and-recreate is the only fix for a wrong-repo PR; never force-push or
rebase to work around a repository-identity mismatch. Do not change
`gh repo set-default` in a checkout the user shares for upstream contributions
without stating the new default.
