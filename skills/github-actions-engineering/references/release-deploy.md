# Release & deployment workflows

CI proves code; release/deploy workflows ship it. Keep them conceptually separate: a PR never deploys production. Typical lifecycle: PR → CI → merge to main → staging → tag/manual gate → production. Do not force this shape where the project's deployment intentionally differs.

## Release design

Before writing a release workflow, inspect: version scheme (do not invent SemVer), tags, package manager, registry, changelog process, signing, deployment relationship. One coherent source of release truth — a pushed version tag, a manual dispatch, or a release-published event — and exactly one workflow reacting to it. Two triggers on one publish path = double publishing.

**Gate publishing on a detected release condition, not any push:** a detect job resolves whether HEAD is a release commit (tag exists, message, release branch merge) and the publish job runs only when detection succeeded. A stray push must never publish.

## Build once, promote the same artifact

```
tag → build → test/verify the artifact → attest (where useful) → publish/deploy THAT artifact
```

Do not verify source state A and then rebuild unrelated state B for release. Exception: platforms that inherently build from source with no artifact handoff — then record the exact commit/ref the platform deployed instead of forcing artifact plumbing.

## Trusted publishing

- Prefer registry trusted publishing / OIDC (PyPI, npm, RubyGems, and others support it) over long-lived registry tokens; grant `id-token: write` only to the publish job.
- Without OIDC: narrowly scoped, dedicated CI tokens — never developer personal credentials. Rotate via the registry, not the repo.
- Release jobs never run from fork-PR contexts. Release environment secrets only exist at the release environment boundary.

## Provenance & attestations

For release artifacts consumers actually verify (binaries, images, packages, SBOMs), consider GitHub artifact attestations — they prove build provenance linkage (source commit → artifact), not artifact security. Requires appropriate `id-token`/`attestations` permissions on the release job. Do not attest routine CI outputs nobody will verify, and do not skip provenance just because the pipeline is internal — record the source ref either way.

## Failure safety

Multi-package releases: build all → validate all → publish; consider per-package failure behavior and document what is non-atomic (e.g. package A published, package B failed). Do not invent rollback machinery the ecosystem does not support — document limitations and add a controlled manual re-run path (`workflow_dispatch`) instead of forcing fake commits.

## Deployment workflows

- Separate BUILD/VERIFY from DEPLOY. Deploy the verified artifact (or the exact ref the platform builds).
- **Environments:** staging and production jobs reference GitHub environments so secrets/approvals/branch restrictions apply at the right boundary. Specify the environment contract (name, secrets, restrictions, approvals) for `github-repo-setup` to configure — do not assume protection exists.
- **Concurrency:** serialize deploys with a stable group (per environment, e.g. `${{ github.workflow }}-production`) and do NOT cancel an in-flight production deploy when a newer commit arrives — queue instead. `cancel-in-progress: false` is the production default; cancellation belongs to PR CI.
- **Manual deployments:** `workflow_dispatch` with typed inputs; deploy jobs never interpolate inputs into shell (see `security.md`).
- **Migrations:** deploy-time DB migrations need explicit thought — ordering, backwards compatibility, irreversibility, concurrent deploys. Do not invent automated rollback the application cannot perform; environment policy matters more than YAML cleverness.
- **Infrastructure repos (Terraform/Pulumi):** PR → validate/plan with scoped read-only cloud roles (OIDC); apply only on trusted events/manual dispatch behind environment approval. Never let an untrusted PR acquire production credentials to produce a plan; if the plan itself needs secrets, that is a design decision to surface, not hide.
- **Production credentials stop at the production boundary.** PR test jobs never receive them — this must be visible from the workflow graph.

## Scheduled & optional checks

Schedules (nightly dependency audit, compatibility suites, fuzzing) run time-dependent work; they execute from the default branch and do not fire on empty schedules in inactive repos (verify current semantics). Expensive useful checks (E2E, benchmarks, extended scans) belong on main pushes, schedules, or label/manual dispatch — but a critical regression check is never demoted to nightly to save minutes.
