<!-- capsule-v2 -->
# SemVer public API — which version digit moves for this change?

**Source:** semver.org 2.0.0 spec rules 6–8, FAQ. **Question:** Given a diff, is this MAJOR, MINOR, or PATCH for consumers?

## Public API boundary
**Signature:** documented or code-enforced surface consumers call.
**Data Shape:** `MAJOR.MINOR.PATCH` integers, no leading zeroes.

**Flow:** classify change against **public API only** → bug fix compat → PATCH; new compat API or deprecation → MINOR (reset patch); break/remove → MAJOR (reset minor+patch).
**Invariant:** released version contents immutable — bad release gets new version, never retag (`spec rule 3`).
**Probe:** changelog + tag + manifest (`package.json` / `pyproject.toml`) agree on `x.y.z`; breaking change absent from PATCH release notes.

## 0.y.z and 1.0.0
**Flow:** initial dev at `0.1.0`; rapid break allowed in 0.y.z; move to `1.0.0` when production/users depend on API stability.
**Invariant:** `0.y.z` carries no stability promise (spec rule 4).

## Deprecation ladder
**Flow:** deprecate in MINOR (docs + changelog `Deprecated`) → at least one minor with warning → remove in MAJOR (`Removed`).
**Invariant:** skipping Deprecated section forces painful jumps (Keep a Changelog).

## Verdict
Adopt spec digit semantics; adapt public API declaration to project docs; omit semver on internal-only repos with no consumers. Learning note: `semver-learning-note.md`.
