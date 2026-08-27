---
name: pi-multi-pass-foundation
description: Use when porting multi-account provider rotation machinery — rate-limit failover planning with auditable skips, forward-only cascade state that survives replay retries, cooldown-gated member eligibility, exact project allow-list policy, fail-open selection strategies, and index-stable config normalization - capsule-v2 source maps with decisive excerpts and graph retrieval.
---
# pi-multi-pass: multi-subscription rotation foundations

## Use this for
Use when building or porting rotation across multiple OAuth accounts per provider: ordering failover candidates when one account hits a rate limit, keeping attempted-account state stable across internal prompt replays, gating members on auth plus cooldown expiry, constraining routing to a per-project exact allow-list, degrading selection strategies safely to default order, and normalizing multi-account config files without losing entries. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/config-normalization-plane.md` — how does multi-account config stay entry-stable across corrupt files and env overlays?
- `references/project-allowlist-policy.md` — how does per-project policy constrain subs, pools, and chains without mutating global config?
- `references/member-eligibility-cooldown.md` — who is eligible right now, and when does a cooled-down member return?
- `references/forward-only-failover-plan.md` — how are failover candidates ordered with an auditable skip taxonomy?
- `references/strategy-reorder-failopen.md` — how do quota/schedule/custom selection strategies degrade without breaking failover?
- `references/cascade-turn-boundary.md` — how does failover survive internal replay retries without re-attempting exhausted accounts?
- `references/quota-snapshot-parsing.md` — how does untrusted provider quota JSON become a worst-case health signal that never throws?
- `references/preset-switch-resolution.md` — how do account switches preserve model id and presets fall back without partial state?
- `references/pool-health-status-reporting.md` — how do you render live rotation health that never disagrees with actual selection behavior?
- `references/quota-dispatch-plane.md` — how do you discover checkable accounts from a checker registry and fan out concurrent health checks that never reject as a batch?
- `references/provider-clone-registration.md` — how do N accounts of one base provider become distinct registered providers sharing one template implementation?
- `references/pool-reference-integrity-writes.md` — how do pool rename/delete keep every chain reference coherent with auditable counts?
- `references/subscription-teardown-cascade.md` — in what order do auth, registration, membership, chains, and the config entry tear down when one account is deleted?
- `references/create-validation-gates.md` — what must be validated against live config before a new pool or chain may persist?

## Capsule map
- **Config plane** - `config-normalization-plane`: defensive normalization plus lowest-free-index (>= 2) merge keeps `${provider}-${index}` identity stable.
- **Policy plane** - `project-allowlist-policy`: exact allow-list filters subs, prunes pool members and emptied pools, then prunes orphaned chain entries.
- **Eligibility gate** - `member-eligibility-cooldown`: lazy cooldown expiry on read; auth check first; exhausted-at timestamps, never counters.
- **Failover planning** - `forward-only-failover-plan`: ring walk inside the pool from the current index, then strictly forward along the owning chain; every exclusion becomes a typed skip.
- **Selection strategies** - `strategy-reorder-failopen`: quota-first/scheduled/custom only REORDER validated candidates; any failure falls back to plan order.
- **Cascade boundary** - `cascade-turn-boundary`: prompt-keyed cascade state; mark-exhausted before planning; record-attempted only after switch; suppress-next-start-turn guards the replay.
- **Quota snapshots** - `quota-snapshot-parsing`: guard -> collapse -> worst-wins merge -> min-fold -> band (blocked<=5/low<=15/watch<=30/ready); garbage input = kind "error", never a throw.
- **Switch resolution** - `preset-switch-resolution`: auth-gated allow-list options; preferred current model id first, base-template walk fallback; checked setModel; presets are ordered fail-continue ladders.
- **Status reporting** - `pool-health-status-reporting`: pure reporters over the planner's own eligibility predicates; fixed diagnostic-label ladder; wrapping-hour schedule algebra shared with strategy ordering.
- **Quota dispatch** - `quota-dispatch-plane`: checker registry drives account discovery; exact allow-list + dedup; one Promise.all with shared abort; unknown base skipped, per-account typed failures, one canonical sort.
- **Provider cloning** - `provider-clone-registration`: template-parameterized OAuth per index; deep-cloned model catalog under `${provider}-${index}`; config persisted before host registration.
- **Reference integrity** - `pool-reference-integrity-writes`: pure rename/prune kernels returning audit counts; confirm -> mutate -> save -> reload-from-disk.
- **Teardown cascade** - `subscription-teardown-cascade`: logout -> unregister -> strip membership -> drop emptied pools -> prune chain refs -> exact entry removal -> single save -> dual cache refresh.
- **Validation gates** - `create-validation-gates`: null-or-first-error validators against live config; structural before referential; model availability judged by the base catalog.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-multi-pass (package.json declares MIT; NO LICENSE/COPYING file at pin — treat as citations-only until provenance resolves), `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory project `pi-multi-pass` (ready FULL mode, 402 nodes / 1495 edges, root = canonical checkout, HEAD = pin, zero parse-partial, zero skipped, .git excluded by design; every cited path no_recorded_issue with generation match 2026-08-24T14:18:05Z).

## Full view (memory graph)
Revalidate `pi-multi-pass` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. All Retrieve blocks below were live-resolved against project `pi-multi-pass` at the pin during passes 1–3 (2026-08-25); probes are the repo's own `tests/*-check.mjs` node scripts, all green at b9d9d1d7a092 including --retry-start-turn/--pool-only/--no-loop/--failure-path modes.

## Boundaries
Adopt the pure routing contracts: candidate planning with typed skips, forward-only cascade state, lazy cooldown algebra, exact allow-list filtering, fail-open strategy reorder, index-stable config normalization. Adapt host integration points (ExtensionAPI event wiring, modelRegistry/authStorage lookups, ui notify/setStatus transport) to your host. Omit pi TUI command handlers, ~/.pi config paths, arbitrary user JS selector execution unless sandboxed, and provider-specific quota scrapers you have not verified.
