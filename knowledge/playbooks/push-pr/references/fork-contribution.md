# Contributing from a fork

Use when the pull request targets a repository the user does not own and the work
lives in a fork. [gh-repo-target-guard](../../gh-repo-target-guard/README.md) owns
which repository a `gh` command targets,
[pre-PR validation](../../pre-pr-validation/README.md) owns the review lanes, and
[CI observation](ci-and-observation.md) owns binding a verdict to a head; this
reference owns the fork workflow around them.

## Keep the remote roles straight

- Conventionally `origin` is the fork and `upstream` is the project. Verify the
  actual fetch/push URLs and write permissions rather than assuming these roles.
  An upstream contribution uses an explicitly requested PR, not a direct push.
- Verify GitHub's fork-network relationship separately from Git ancestry. A
  same-named copy may share commit history without belonging to that network;
  neither its name nor a common ancestor establishes cross-repository PR support.
- Preserve existing disabled upstream push URLs. Adding one can prevent mistakes,
  but changing checkout configuration is a separate scoped choice, not an
  automatic side effect of contributing.

## Branch from the project's base

- Fetch `upstream` and branch from the project's base (`upstream/main`), so the
  branch starts from the revision the project reviews, not from a fork default
  branch that may be stale.
- Keep one branch per contribution. For a contribution-only fork, a sync-only
  default branch simplifies future work. A downstream fork may intentionally keep
  features on its default branch; do not erase them to enforce that convention.
  [Fork synchronization](../../git-workflow-and-versioning/references/fork-sync.md)
  owns updating that fork, including reusing an existing integration while its
  upstream PR is still under review.

## Keep the branch current

- When currency or conflicts require an update, inspect ancestry and existing
  integrations first; base movement alone is not permission to rewrite the branch.
  Resolve authorized integrations locally and rerun affected checks. GitHub's
  "Sync fork" control or `gh repo sync <fork> -b <branch>` is not a substitute for
  preserving divergent fork work; a forced sync can discard it.
- On a branch already open for review, a non-rewriting merge often preserves
  reviewers' context. Follow project policy; any new head needs revision-bound
  evidence, and rewriting published history needs explicit approval.
  [git-workflow-and-versioning](../../git-workflow-and-versioning/README.md) owns
  base comparison and squash-merge reconciliation.

## Open the PR against the project, and read its CI where the PR lives

- Create it with `--repo <project>` and `--head <fork-owner>:<branch>`, then confirm
  the URL belongs to the project and the base is the project's base branch. The
  fork's branch is the head, never the base.
- Read the PR's checks in the base repository. Normal public fork
  `pull_request` workflows use read-only tokens, no secrets, and may wait for
  maintainer approval; inspect the actual event and policy rather than assuming
  every check uses that execution context.
  [github-actions-engineering](../../github-actions-engineering/references/security.md)
  owns those fork-PR token and runner rules. A missing or queued check is not a
  failing one.
- Local and fork-side runs are not the PR's verdict. Record the fork and base
  mapping and the revision actually tested.
- Fork commits keep the fork's SHAs, while a squash merge upstream creates new ones.
  Identify the merged record by upstream's merge commit, not by matching commit
  hashes. [Fork replication](../../git-workflow-and-versioning/references/fork-replication.md)
  owns comparing a fork PR's contents with an upstream PR's.

## Verify

- Fetch/push URLs map to the intended fork and project; no contribution commit
  was pushed to an unauthorized target.
- The PR URL names the project, its base is the project's base branch, and its head
  is `fork-owner:branch`.
- Local evidence identifies the head under review; CI also identifies its tested
  revision when a synthetic merge is used. The fork's default branch matches its
  intended role, whether an upstream mirror or a maintained downstream branch.
