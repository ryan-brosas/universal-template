# Changelog style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `changelog-*.md` capsules, `git-workflow-and-versioning`, `push-pr`.

## Sources read

| Source | What we extracted |
|---|---|
| [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) (CC BY 4.0) | Human audience, `[Unreleased]`, change types, ISO dates, anti-patterns (git log diffs, missing deprecations, inconsistent entries, yanked) |
| Paired | `semver-learning.md` — version headers must match semver tags |

## Mental model

A changelog is a **curated product narrative** between releases — not a VCS dump. Each version section answers: *what should a human upgrading care about?* Group by **change type** (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`) so scanners find breaking paths fast. `[Unreleased]` is a **staging area** moved wholesale into a dated version at release.

Git commits explain *how the code evolved*; changelog entries explain *what users experience* — often one entry summarizes many commits.

## File contract

- Path: **`CHANGELOG.md`** (uppercase, root).
- Header: state semver adherence.
- Order: **newest first** (reverse chronological).
- Version headers: `## [1.2.0] - 2026-08-28` — ISO 8601 date only.
- Linkable: compare URLs between tags at bottom (`[1.2.0]: https://...compare/v1.1.0...v1.2.0`).

## Change-type semantics

| Section | Consumer question |
|---|---|
| Added | What can I use now? |
| Changed | What behaves differently? |
| Deprecated | What must I migrate before next major? |
| Removed | What broke my build? |
| Fixed | What bug stopped hurting me? |
| Security | What CVE/class of issue? |

Empty sections: omit (noise).

## Release workflow

1. During dev: bullets under `[Unreleased]` by type.
2. On release: rename `[Unreleased]` → `[x.y.z] - YYYY-MM-DD`; bump semver in manifest; tag.
3. Open fresh empty `[Unreleased]`.

Pairs with semver bump rules — version in changelog, tag, and package manifest must match.

## Deprecation + semver bridge

Upgrade path for breaking removal:

1. Release **minor** with `Deprecated` entries (still works).
2. Users migrate.
3. Release **major** with `Removed` entries.

Skipping Deprecated section → painful upgrades (Keep a Changelog "Ignoring Deprecations").

## Special cases

- **Yanked:** `## [0.0.5] - 2014-12-13 [YANKED]` — loud, parseable.
- **Inconsistent changelog:** partial entries worse than none — users trust it as truth.
- **GitHub Releases only:** fine for GitHub UX; not portable — prefer `CHANGELOG.md` in repo.

## Anti-patterns

| Pattern | Why |
|---|---|
| `git log` paste | Merge commits, WIP, internal refactors |
| Version without date | Hard to correlate with support tickets |
| US-style dates | Ambiguous globally |
| Breaking change only in commit body | Users don't read commits |

## Skill trace

- Capsule: `changelog-human-curation.md`
- Application: `git-workflow-and-versioning` step 7 (version surfaces), `push-pr` (release PR body may cite changelog section)
