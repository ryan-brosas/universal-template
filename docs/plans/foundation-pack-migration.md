# Work record: Foundation Pack migration

## Verified pass

Closed 2026-09-02 for the current checkout. All 194 Foundation Pack leaves received an evidence-backed provenance disposition; every safely retained exact-pin source was sequentially re-indexed in Codebase Memory with `mode: "full"` and verified ready with coverage and an architecture graph probe. No Codebase Memory project was deleted.

| Disposition | Leaves | Verified outcome |
| --- | ---: | --- |
| retain | 85 | Recorded project exists; checkout is a Git root at the recorded pin; full-mode index, status, coverage, and graph probe succeeded. |
| revise → retained | 2 | `dub-foundation` and `grist-core-foundation` had checkouts beyond their recorded pins; revise closure (2026-09-02): checkout HEAD == recorded pin, origin behind 0, refs==loaders, validator 0 fail per leaf. |
| defer | 107 | 82 identities are absent from the current graph, 21 leaves lack Codebase Memory provenance, 1 root is missing, and 3 leaves lack a parseable source pin. |

The pilot `aeo-affiliate-skills-foundation` was verified at its exact MIT source pin: `bun run test:registry` and `bun run test:docs` passed. Its full index is ready, with only the pre-existing documented partial HTML ranges.

## Source and evidence

- Foundation claims: `foundation-pack/`
- Structural verification: `scripts/foundation-validator.py`
- Exact-source and full-index triage: project Hindsight bank `foundation-pack-migration-triage-2026-09-02`
- Retention and deferral were based on direct source, tests where available, recorded source pins, index status/coverage, and bounded graph probes. Codebase Memory remained a retrieval surface, not source of truth.

## Decision and counter-evidence

Only exact-pin sources with a verified checkout were re-indexed. Current-head graph output does not replace source facts: the two drifted sources were marked `revise`, and missing or unparsable provenance was marked `defer` rather than guessed or silently retained. Hindsight preserves decisions and counter-evidence, not raw source or graph output.

## Omitted or unresolved

The 109 `revise`/`defer` leaves are an explicit source-recovery backlog. They require pinned-source and direct-test review before any capsule rewrite, re-index, or demotion. OpenViking remains manual and opt-in; its disabled Pi extension was not a migration blocker.

## Next target

Corrected census-aware triage (2026-09-02 review). The live census has 168
projects; a per-leaf scan of every recorded Codebase identifier plus a
checkout sweep shows 190 of 194 leaves are either census-indexed or have a
git checkout. The residual backlog is exactly 4 internal-only leaves:
`dsh-factory-foundation`, `pi-autoresearch-foundation`,
`pi-messenger-swarm-foundation`, and `pi-supervisor-foundation`, whose
indexes were removed in the prior stale-index cleanup (#35).

Recover those four through /inspo approval and re-index at the recorded
pin. Family aliases (`mcp-spec-and-servers` to modelcontextprotocol and
servers, `jetbrains-internals` to the jetbrains-* family, `roo-foundation`
to Roo-Code, `dnd-kit` to ui-dnd-kit) are indexed and are not missing; do
not classify by leaf name alone. Never demote silently: any unindexed leaf
without a checkout gets a written liveness note first. Gates stay green
throughout.
