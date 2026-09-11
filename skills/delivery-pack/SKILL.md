---
name: delivery-pack
description: "Use when committing or reconciling Git, pushing, opening or reviewing PRs, shipping through merge, configuring GitHub or Actions CI, deploying, or publishing releases and npm packages. Local code/test failures belong to engineering-pack."
invocation: entry
---

# Delivery pack

Choose the requested operation, not a larger lifecycle. Read its procedure and
only the references needed. Paths and helper commands belong to the selected
procedure's directory, not this router.

- Commit, branch, reconcile squash merges, version or tag:
  [git-workflow-and-versioning](../../knowledge/playbooks/git-workflow-and-versioning/README.md).
- Push, open/update a PR, handle review threads, or merge an existing PR:
  [push-pr](../../knowledge/playbooks/push-pr/README.md).
- Explicitly ship end to end through CI, reviews and merge:
  [ship-pr](../../knowledge/playbooks/ship-pr/README.md).
- Wrong GitHub target or fork ambiguity:
  [gh-repo-target-guard](../../knowledge/playbooks/gh-repo-target-guard/README.md).
- CI workflow creation, repair or hardening:
  [github-actions-engineering](../../knowledge/playbooks/github-actions-engineering/README.md).
- Repository rules, labels and governance:
  [github-repo-setup](../../knowledge/playbooks/github-repo-setup/README.md).
- npm publishing from Actions:
  [npm-trusted-publishing](../../knowledge/playbooks/npm-trusted-publishing/README.md).

For deployment, launch, contribution discovery or review-specific tooling, choose
one entry in [other delivery procedures](references/topics.md). A push request
never implies permission to merge. Trivial work needs no procedure ritual.
