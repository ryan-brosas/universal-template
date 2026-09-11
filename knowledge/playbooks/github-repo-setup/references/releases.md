# Release settings - authority, notes, tag policy, immutability

## Authority (decide with git-workflow-and-versioning)

One authority per repository. Default for GitHub-native projects: the `vX.Y.Z`
tag is the truth; release CI verifies the tree and publishes with generated
notes. Alternatives (curated CHANGELOG, Release Please, semantic-release)
belong to the versioning skill; this skill only wires the GitHub side.

## Generated notes: `.github/release.yml`

Categories are label-driven, so the PR metadata chain feeds them: PR title ->
`type:*` / `breaking-change` labels, changed paths -> `area:*` labels, merged
PR -> categorized notes. Current schema:

```yaml
changelog:
  exclude:
    labels: [release:skip]
  categories:
    - title: Breaking Changes
      labels: [breaking-change]
    # ...
    - title: Other Changes
      labels: ["*"]
```

Every label referenced here must exist (create the taxonomy first). Area
labels describe seams; do not turn them into note categories.

## Tag protection (ruleset)

For versioned projects, protect `refs/tags/v*`: block deletion and update.
Restrict creation only after confirming the project has no moving
major-version tags (`v1`, `v2` - common for GitHub Actions repos). Read the
ruleset back after creation.

## Immutable releases

Relevant when published assets must stay fixed (distributed binaries,
packages). Verify current support in Settings > Releases and via the repo
edit API; enable only when the repository actually publishes assets. With
immutability on, publish via draft -> verify -> publish, and do not plan to
edit published bodies/assets.

## Attestations

Artifact attestations add provenance for artifacts distributed outside
GitHub Releases (binaries, containers). A config repository that publishes no
build artifacts skips them deliberately - GitHub's own release provenance
covers the release object; do not duplicate provenance for check-count
inflation.

## Release workflow ownership

The release workflow (verify tag -> gates -> publish) is
`github-actions-engineering` work; this skill owns the repo-level release
settings (features, tag rulesets, immutable-release setting) and the notes
category mapping.
