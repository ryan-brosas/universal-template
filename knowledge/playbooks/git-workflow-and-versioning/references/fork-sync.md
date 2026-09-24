# Synchronize a fork without replaying finished work

Use when asked to update or rebase a fork, especially while an upstream PR is
waiting. The desired result is current upstream content plus the fork work the
user wants to keep; a rebase is only one possible mechanism.

## Choose from the graph, not the verb

Confirm the authorized repository and branch with the
[target guard](../../gh-repo-target-guard/README.md). Fork-only permission does not
extend to the upstream PR, releases, deployments, or review closure. Inspect
push-triggered effects and branch policy before choosing a direct push.

Fetch both repositories. Pin the fork tip, upstream tip and any existing
integration candidate; inspect its content, not just its name or version.

```sh
git merge-base --is-ancestor <fork-tip> <candidate>
git merge-base --is-ancestor <upstream-tip> <candidate>
```

If both succeed, the candidate can advance the fork without replaying the work.
Reuse it when its content matches the requested scope. If the fork already points
there, verify rather than pushing again. If ancestry fails, distinguish a stale
candidate from divergent fork work; propose the needed integration instead of
forcing a sync. Rebasing published history needs explicit authorization.

A contribution-only fork may mirror upstream on its default branch. A downstream
fork may deliberately keep features there. Preserve that intent; upstream approval
need not block a separately authorized fork update, but fork branch protections
and applicable review requirements still apply.

## Validate without disturbing the active checkout

Use a detached disposable worktree at the pinned candidate when the active checkout
is dirty or supplies a running application. Keep a path/content/status baseline
covering relevant untracked files and artifacts; status alone cannot detect edits
inside an already-dirty file. Run the project's required install, focused tests,
probes and build there. Reuse valid evidence for unchanged revisions rather than
restarting all checks after a continuation.

Attribute findings before changing anything: an identical upstream blob can explain
inherited formatting, not exempt it from a required gate. Disclose the finding and
follow the project's policy; a promotion request is not permission for unrelated
cleanup or changed test expectations.

## Promote only the validated revision

Refresh refs before pushing; recheck ancestry, candidate identity and clean content.
Confirm the fork's push URLs explicitly; remote names are only conventions.
Dry-run the exact refspec, then use a non-force push with implicit tag pushing off:

```sh
git -c push.followTags=false push --dry-run --porcelain <fork-remote> <candidate>:refs/heads/<branch>
git -c push.followTags=false push --porcelain <fork-remote> <candidate>:refs/heads/<branch>
```

Read the branch back with `git ls-remote <fork-remote> refs/heads/<branch>`.
A rejection or concurrent change calls for inspection, not force or policy bypass.
After an interrupted call, read back first; a missing tool return is not proof that
the push failed.

If updating the local branch is also in scope, check `git worktree list --porcelain`
first. Never move a branch checked out in any worktree behind that checkout's back.
For an unchecked-out branch, confirm its recorded old tip is an ancestor, then use
`git update-ref refs/heads/<branch> <candidate> <recorded-old>` for compare-and-swap.
A mismatch requires inspection. Leave the active branch, index and files alone.

## Verify and report

Follow [CI observation](../../push-pr/references/ci-and-observation.md) for the new
fork push, not the upstream PR's runs. Recheck the original worktree baseline.
Report the remote/local tips, checks actually run, evidence location and remaining
review gaps concisely. State where the build ran: advancing refs does not update
the active checkout or activate an installed runtime. Describe preservation only
for the checkpoints actually compared.
