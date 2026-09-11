# Arbor evidence inventory

## Provenance

Upstream: https://github.com/penso/arbor; revision
`d8d82b7eec6cba3682374875d8f13407c7181ef0`; MIT (`LICENSE`).
Checkout: `<local-checkouts>/arbor`; origin and approved HEAD matched and
the working tree remained clean in this round. Upstream freshness beyond the pin
was not checked. Existing full graph: `heddlework-inspo-arbor`.
These passes used direct source navigation, not graph queries or refreshes.

## Complete capsule inventory

- [Control-key/text followup](control-text-followup.md): How is a control key
  delivered once when keydown and IME text both fire? **ADAPT**, conditional on
  reproducing duplicate delivery locally and adding session/focus ownership.
- [Delayed output following](delayed-output-following.md): Can queued following
  override a manual scroll or survive terminal selection changes? **ADAPT**,
  preserving callback revalidation rather than transplanting window-global state.
- [Bounded scrollback eviction](bounded-scrollback-eviction.md): Does a detached
  viewport preserve surviving rows when the retained prefix is evicted? **ADAPT**,
  separating retention progress from net length and defining expired-anchor policy.
- [Alternate-screen history ownership](alternate-screen-history-ownership.md): Is
  saved alternate-buffer storage equivalent to active alternate mode? **ADAPT**,
  preserving explicit emulator-derived mode and separating viewport policy.

Load one matching capsule and revalidate its source/tests. Current project
requirements, source, tests and runtime behavior outrank this evidence.

## Scope and evidence

Four recorded seams, not repository-wide coverage. Prior capsules retain their
original evidence: 12 local input/service tests with 48 assertions; then 9 service
tests with 34 assertions plus a two-session following/cleanup probe. The delayed
following capsule distinguishes production scheduling from a test-only retry helper.

This round studied two successive questions and added two capsules. The service
and VT modules passed **24 tests / 95 assertions**. Injected `bun -e` probes
characterized three gaps despite those passing tests: cap saturation drifts a
surviving detached anchor; primary history stops growing after an alternate
round-trip; detached alternate entry mixes primary history and alternate rows.
Characterization assertions exited 0; they confirm observed behavior, not fixes.
The oldest-retained-row probe also showed unavoidable anchor expiry. Probes
cleaned up the service and verified listener removal; the cap probe verified kill.

Upstream tests were inspected, not executed. Arbor's history-inclusion tests run
below its default cap; its synthetic offscreen-hash test is not eviction coverage.
Its mode test and key-encoding test do not establish detached alternate-screen
policy or post-return history growth. The Alacritty dependency's internal retention
algorithm was not inspected. No setup, installs, builds, remote updates, index
refreshes, app edits or reference checkout mutations were performed. Native
geometry/event ordering and upstream integration behavior remain unverified.

## Exclusions and next seam

The PTY reader/snapshot boundary was read only as needed for ownership; this is
not a PTY lifecycle audit. Daemon persistence, remote runtimes, experimental
Ghostty and unrelated UI remain outside this round. No Arbor native cap-eviction
defect was reproduced, and neither local gap has been fixed here.

NEXT: does selection/copy rebase or invalidate row coordinates after prefix
eviction or screen replacement, or silently copy different text? Stop this round
after its two bounded questions. Inventory completeness refers only to the four
actual capsule files, not exhaustive learning of Arbor.
