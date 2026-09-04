# Work record: historical foundation migration

## Verified pass

Closed 2026-09-02 for the current checkout. All 194 foundation leaves received a provenance disposition; every safely retained exact-pin source was re-indexed in Codebase Memory with `mode: "full"` and verified with coverage plus an architecture-graph probe. The disposition table is the adoption snapshot for the migration pass.

| Disposition (snapshot) | Leaves | Evidence here |
| --- | ---: | --- |
| retain | 85 | Recorded project exists; checkout is a Git root at the recorded pin; full-mode index, status, coverage, and graph probe succeeded. |
| revise → retained | 2 | `dub-foundation` and `grist-core-foundation` had checkouts beyond their then-pin; closed 2026-09-02 (HEAD == recorded, origin behind 0, refs==loaders, validator 0 fail). |
| defer (snapshot) | 107 | At snapshot time: 82 identities absent from the graph, 21 lacked provenance, 1 root missing, 3 pins unparsable. |

## What changed on re-triage (2026-09-02)

Re-evaluated the 107-leave `defer` bucket against the live census and on-disk checkouts, using every recorded Codebase identifier (not the leaf-name only), so a leaf is evidenced when its project id exists in the census or its root is a real git checkout. Result: **190 of 194 leaves were evidenced** at that point; the 4 internal-only leaves were then recovered (below):

- `dsh-factory-foundation`
- `pi-autoresearch-foundation`
- `pi-messenger-swarm-foundation`
- `pi-supervisor-foundation`

Family-alias names (e.g. `mcp-spec-and-servers` → modelcontextprotocol + servers, `jetbrains-internals` → jetbrains-* family, `roo-foundation` → Roo-Code, `dnd-kit` → ui-dnd-kit) are not missing; they matched the census under their primary recorded IDs.

## Next target

Resolved 2026-09-02: the four residual leaves were re-indexed at their recorded pins in full mode and are ready in the Codebase Memory census (`mnt-hdd-utopia-inspo-external-ext-dsh-factory` 900n/3408e, `...-pi-autoresearch-harness` 658n/1508e, `...-pi-messenger-swarm` 2493n/5802e, `...-pi-supervisor` 504n/1304e; 0 skipped each, parse_partial per capsule caveat). Each leaf carries a dated recovery note. No residual backlog remains: all 194 leaves are now evidenced.

Keep exact metadata, reference, and repository contract checks green; never demote silently in future passes.

## Source and evidence

- Foundation claims: `skills/*-foundation/`
- Structural verification: foundation metadata and references through `scripts/skill-validator.py`
- Snapshot triage bank: `foundation-pack-migration-triage-2026-09-02`
- Retention/deferral based on direct source, tests, recorded pins, index coverage, and bounded probes. Codebase Memory stays a retrieval surface, never the source of truth.
