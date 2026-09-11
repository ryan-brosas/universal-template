# Omarchy evidence index

## Provenance

- Upstream: https://github.com/basecamp/omarchy
- Revision: `a9eaf7978e33a6832630c51f1bb87f97dbf5fe36`
- License: MIT
- Checkout: `<local-checkouts>/omarchy`
- Existing full-mode index: `heddlework-inspo-omarchy`

Origin and HEAD were verified against the approved pin; the checkout was clean.
This pass used direct source and test reads; it did not re-index or claim current
graph completeness. No upstream dependencies or setup scripts were run.
Current project source, tests, requirements and runtime behavior outrank this evidence.

## Complete capsule inventory

- [staged theme activation and independent palette-reader failure boundaries](staged-theme-reader-boundary.md) — What can a palette reader assume while a serialized writer removes and replaces active state?

- [installed-theme staging](installed-theme-staging.md) — Recursive symlink rejection, top-level denylist limits, provenance exceptions and scratch extraction. **ADAPT**; direct hostile-theme tests inspected, not executed.
- [legacy palette contract](legacy-palette-contract.md) — Narrow extraction grammar, duplicate precedence, missing-normal success/no-output and bright-before-primary fallbacks compared with the local semantic reader. **ADAPT**; parser edge cases are source inference, not upstream test execution.

## Latest round: two bounded questions

Added the two capsules above; preserved the prior reader-boundary capsule. Origin,
approved HEAD and clean upstream state were checked. No upstream scripts, setup,
remote updates or indexing ran. Direct source owns evidence; no graph coverage claim.
`bun test ./tests/theme-omarchy.test.ts` passed 11 tests / 25 assertions (exit 0).
An injected production-reader probe passed nine assertions for parser differences,
missing-read recovery and idempotent watcher cleanup; its printed count of eight
was a reporting typo. No application/test code changed. Neither local check proves
upstream hostile-theme safety or live desktop behavior.

NEXT: modern `omarchy-theme-color` semantic aliases, defaults and malformed values.
Deferred for review between rounds; no exhaustive learning claim.

## Prior pass scope, evidence and limits

One writer/reader boundary, with theme-staging-test.sh assertions for installed-theme trust policy. Writer locking is not reader atomicity. Current active state uses .local/state, not the older .config path. Excludes whole-distro installation and compositor policy.

The capsule contains the execution path, invariants, failure/cleanup boundaries,
exact source/test pointers, one disposition and the Heddlework comparison.
Upstream tests were inspected, not executed. No live-native validation is claimed.
The local window, theme, terminal-key and terminal-service modules passed together:
27 tests, 88 assertions. These tests establish only their local mocked/pure boundaries,
not upstream behavior. No application code changed.

## Retrieval check

For the question above, select this capsule from this index; its named symbols and
source-relative paths reconnect to the recorded checkout. All local Markdown links
are mechanically checked. Inventory completeness concerns this foundation, not the repository.
