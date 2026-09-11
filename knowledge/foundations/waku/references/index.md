# Waku evidence index

## Provenance

- Upstream: https://github.com/egoist/waku
- Revision: `1114d4c5bdd3baf1454667bd7dd73ddd767a4767`
- License: GPL-3.0-only; architecture-only study, no implementation copying
- Checkout: `<local-checkouts>/waku`
- Existing full-mode index: `heddlework-inspo-waku`

Origin and HEAD were verified against the approved pin; the checkout was clean.
This pass used direct source and test reads; it did not re-index or claim current
graph completeness. No upstream dependencies or setup scripts were run.
Current project source, tests, requirements and runtime behavior outrank this evidence.

## Complete capsule inventory

- [signed archive staging, extraction validation order and cleanup ownership](archive-validation-order.md) — Which gates run before an update becomes an accepted staged layout, and who removes failed staging?

- [Update handoff and readiness](update-handoff-readiness.md) — Helper acceptance versus activation, startup readiness and rollback limits. ADAPT, architecture-only. Direct helper tests inspected, not executed.

## Latest round

One additional bounded pass completed directly after worker prompt delivery failed. Prior capsule preserved. No upstream execution or app changes. Next questions remain in the new capsule; this is not exhaustive learning.

## Scope, evidence and limits

One update-staging boundary. Direct tests establish usable key parsing, rejected path-like versions and valid-root extraction/layout. Malicious archive guard coverage is not inferred from a happy-path test. Excludes daemon/agent internals and installer implementation.

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
