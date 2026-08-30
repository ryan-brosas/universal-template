# Semantic Versioning — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `semver-*.md` capsules, `git-workflow-and-versioning`, release tooling.

## Sources read

| Source | What we extracted |
|---|---|
| [semver.org spec 2.0.0](https://semver.org/) (CC BY 3.0) | MUST rules 1–11, precedence algorithm, BNF grammar, FAQ (0.y.z, deprecations, accidental breaks, `v` prefix) |

## Mental model

SemVer is a **contract language** between publisher and consumer. The public API is the boundary — only changes *at that boundary* drive MAJOR/MINOR/PATCH. Version numbers are **immutable labels** for released artifacts; fixing a bad release means a **new** version, never mutating an old tag. Pre-release (`-rc.1`) signals lower precedence; build metadata (`+sha`) is invisible to precedence.

Dependency ranges like `>=1.4.0 <2.0.0` only work if publishers honor the contract.

## Decision table (public API changes)

| Change | Bump | Reset |
|---|---|---|
| Backward-compatible bug fix | PATCH | — |
| New backward-compatible API | MINOR | patch → 0 |
| Mark API deprecated (still present) | MINOR | — |
| Remove or break API | MAJOR | minor & patch → 0 |
| Only internal/private change | PATCH or MINOR (if new capability) | per FAQ |

**0.y.z:** unstable; treat as no compatibility promise. Start `0.1.0`, increment minor during rapid iteration. **1.0.0** when production/users depend on stability.

## Precedence (comparison)

Compare in order: major → minor → patch → pre-release identifiers.

- `1.0.0-alpha` < `1.0.0`
- `1.0.0-alpha.1` < `1.0.0-alpha.beta` (numeric vs lexical rules per spec §11)
- Build metadata ignored: `1.0.0+build1` == `1.0.0+build2` for precedence

## Deprecation path (spec FAQ)

1. **Minor** release: deprecate in docs + runtime signals if any.
2. At least one minor with deprecation before **major** removes API.
3. Changelog `Deprecated` section documents the bridge (pairs with `changelog-style-learning.md`).

## Immutability

> Once a versioned package has been released, the contents MUST NOT be modified.

Yanked releases (see changelog note) still get a `[YANKED]` entry — the tag may exist but must not be consumed.

## Edge cases (FAQ)

- Broke compat in a minor → release new minor restoring compat; don't rewrite old tag.
- Accidental major behavior in patch → judgment: if users depend on bug, major may be honest.
- `v1.2.3` tag name vs semver `1.2.3` — tag may carry `v`; semver string does not.

## Anti-patterns

| Pattern | Why |
|---|---|
| Re-tagging `1.0.0` with different tarball | Violates immutability; breaks lockfiles |
| Breaking change in PATCH | Destroys range trust |
| No declared public API | SemVer meaningless — boundary unknown |
| 0.y.z promise of stability | Contradicts spec |

## Skill trace

- Capsules: `semver-public-api-and-bumps.md`, `semver-precedence-and-prerelease.md`
- Application: `git-workflow-and-versioning` (version bump + tag step)
