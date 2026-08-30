<!-- capsule-v2 -->
# Changelog curation — what belongs in CHANGELOG.md vs git history?

**Source:** Keep a Changelog 1.1.0. **Question:** How do users learn what changed without reading every commit?

## Human changelog seam
**Path/Symbol:** `CHANGELOG.md` repo root.
**Signature:** `# Changelog` → `[Unreleased]` → `[x.y.z] - YYYY-MM-DD` sections newest first.
**Data Shape:** grouped `Added|Changed|Deprecated|Removed|Fixed|Security` bullets.

### Decisive anti-pattern
```text
# BAD — git log dump
* Merge pull request #123 from ...
* fix typo
* WIP
```

**Flow:** dev bullets under `[Unreleased]` by type → on release rename section, ISO date, semver bump, git tag → fresh empty `[Unreleased]`.
**Invariant:** changelog entry = **user-visible** delta; commits = implementation trail — conflating them hides breaking changes (Keep a Changelog guiding principles).
**Probe:** release PR shows CHANGELOG section for version; no merge-commit noise; `Deprecated` present before `Removed` in semver major.

## Yanked releases
**Flow:** `## [0.0.5] - 2014-12-13 [YANKED]` — still listed, loudly marked.
**Invariant:** consumers must not silently install yanked versions.

## Verdict
Adopt Keep a Changelog structure + ISO dates; pair with `semver-public-api-and-bumps.md`; omit empty sections. Learning note: `changelog-style-learning-note.md`.
