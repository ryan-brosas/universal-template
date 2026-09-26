---
name: delivery-pack
description: "Use when committing or reconciling Git, pushing, opening or reviewing PRs, shipping through merge, configuring GitHub or Actions CI, deploying, or publishing releases and npm packages. This pack owns delivery state; combine it with the pack responsible for the artifact. Local code/test diagnosis remains engineering's boundary."
invocation: entry
---

# Delivery pack

Choose only the requested delivery operations, not a larger lifecycle. Start with
the narrowest matching procedure and add another only when the requested workflow
crosses delivery stages. Read only the references needed; paths and helpers belong
to each selected procedure's directory, not this router.

- Commit, branch, reconcile squash merges, version or tag:
  [git-workflow-and-versioning](../../knowledge/playbooks/git-workflow-and-versioning/README.md).
- Validate finished changes before a PR — required for every PR:
  [pre-pr-validation](../../knowledge/playbooks/pre-pr-validation/README.md).
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

For deployment, launch, contribution discovery or review-specific tooling, select
additional [delivery procedures](references/topics.md) only for distinct active
operations. A push request never implies permission to merge. A trivial change
needs no procedure ritual, but every PR still runs pre-pr-validation.
