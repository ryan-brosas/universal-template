<!-- capsule-v2 -->
# SemVer precedence — how do `-alpha`, `-rc.1`, and `+build` sort?

**Source:** semver.org 2.0.0 rules 9–11, BNF. **Question:** Is `1.0.0-rc.1` safe to consume before `1.0.0`?

## Pre-release precedence
**Signature:** `MAJOR.MINOR.PATCH-prerelease+buildmetadata`.
**Data Shape:** pre-release identifiers after `-`; build after `+`.

**Flow:** compare major → minor → patch numerically → if equal, pre-release **lower** than release (`1.0.0-alpha` < `1.0.0`) → compare pre-release identifiers left-to-right (numeric vs lexical rules in spec §11).
**Invariant:** build metadata does not affect precedence (`1.0.0+001` == `1.0.0+002` for ordering).
**Probe:** semver comparator tests or `npm semver` / language equivalent: `1.0.0-rc.1` < `1.0.0` < `1.0.1`.

## Tag naming
**Flow:** git tag may be `v1.2.3`; semver string remains `1.2.3` (FAQ).
**Invariant:** dependency ranges use semver numbers, not necessarily the `v` prefix.

## Verdict
Adopt full precedence algorithm for range tooling; adapt pre-release channel names to project (`-beta.2`, `-rc.1`). Learning note: `semver-learning-note.md`.
