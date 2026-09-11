<!-- capsule-v2 -->
# History and merge — when may history rewrite, and how do branches land?

**Source:** agis/git-style-guide; Git `SubmittingPatches` (patch series rewrite). **Question:** What history is shared truth vs private draft?

## Published vs private history
**Path/Symbol:** `git push`, `git rebase`, `git merge`.
**Signature:** shared refs (`origin/main`, release tags) vs local-only/feature branches.
**Data Shape:** published = append-only; private = mutable until push.

**Flow:** local WIP commits allowed → before push: squash/fixup/rebase -i → push → **never** force-push shared branches without explicit user approval.
**Invariant:** rewriting `main` invalidates others' clones and CI baselines — agis "do not rewrite published history."
**Probe:** `git reflog` vs remote: no force-push to protected branches; `gh pr view` merge strategy matches team doc.

## Merge seam
```shell
git fetch origin
git rebase origin/main    # linear-history teams
git merge --no-ff feature # preserve branch topology (when policy says so)
```

**Flow:** test before push → rebase or merge per policy → merge commit vs squash per project → delete merged branch.
**Invariant:** half-done work must not reach shared remote (agis "test before push").
**Probe:** CI green on PR head; merge commit exists if `--no-ff` required.

## Tags
**Flow:** releases → annotated tag (`git tag -a v1.2.0`); semver string `1.2.0` (see `semver-precedence-and-prerelease.md`).
**Invariant:** tag points at commit that passed release gates.

## Verdict
Adopt append-only shared history; adapt squash-merge vs `--no-ff` to project; omit force-push on shared refs. Learning note: `git-style-learning-note.md`.
