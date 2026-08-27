# Durable learning ledger for memory-graph-skill-miner

This reference documents the durable learning ledger — the host-neutral scheduling
and resume index of the mining loop (the successor of Hermes' OpenViking
llm-repo-learning resource). Keep it under the resolved inspiration root. It is a
scheduling and resume index, not a replacement for source work records or foundation
capsules.

Canonical storage is `/mnt/hdd/utopia/inspo/.skill-mining-work/llm-repo-learning.md`;
per-source records live under `/mnt/hdd/utopia/inspo/.skill-mining-work/<source-slug>/`.
Legacy `<source-slug>-work` directories are no longer canonical and must not be recreated;
the completed migration moved records into `.skill-mining-work/` and archived collision-preserving
originals under `/mnt/hdd/utopia/archive/skill-mining-legacy-20260826/`.

## Row contract

Keep one row per mined source:

| Source | Foundation | Graph project | Pin | Pass | Refs | V2 | Last pass | Next-pass targets | Blockers |
|---|---|---|---|---:|---:|---:|---|---|---|
| repo-slug | leaf-name | project-name | branch@commit | 0 | 0 | 0 | never | concrete paths or seams | unresolved items |

## Status board

The ledger carries a machine-readable `## Status board` section: one line per source
with status `active` / `complete` / `blocked`. The scheduler picks the oldest `last
pass` among `active` rows; `complete` rows are re-verified only (pin/counts/parity)
and return [REPO-COMPLETE]; `blocked` rows stay parked until the blocker clears.

- `complete` only when next-pass targets are empty AND the coverage matrix shows 0
  uncited reusable seams (every omission recorded with a reason).
- Any HEAD advance past the pin reopens a `complete` row to `active` with FULL
  re-index + diff-first re-adjudication before new citations.
- A lane updates its own board line in the same write as its row; it never rewrites
  sibling lines.

## Update protocol

1. Read the entire current ledger before selecting or updating a row.
2. Match the source by slug, graph project, and pin; do not create a duplicate row
   because an alias or graph twin has a different spelling.
3. Update only the owned row and its next-pass targets. Preserve sibling rows byte-for-byte.
4. Re-read the result and verify one row, one pipe shape, current counts, and the
   exact target paths. If a write outcome is uncertain, inspect before retrying.
5. The row is not delivered until the source work record names the same pass, counts,
   modules, blockers, and next-pass targets.

## Hermes-style batch contract

For an autonomous scheduled invocation (any host), the work record must show this order:

1. **Learning note first:** mental model, architecture/boundaries, invariants,
   selected connected subsystem, prior covered/partial/uncited seams, and porter
   questions. This note prevents the next pass from repeating the same study.
2. **Production batch:** target 5–8 distinct source-confirmed capsule-v2 outcomes
   (target six), including substantive refactors when they close a real gap. Never
   pad with duplicate or shallow references.
3. **Resume state:** exact changed files, tests/probes, parity, omitted reasons,
   blockers, cumulative counts, and concrete next-pass targets. Counts in the ledger,
   work record, and leaf map must agree.

If fewer than five outcomes remain, record evidenced closure; if evidence or a runner
blocks the batch, record the blocker instead of claiming a successful learning pass.

## Honest status values

- A ready graph is graph-indexed, not learned.
- A capsule count is not a completeness proof.
- A missing test runner is blocked, not passing.
- An unresolved license is a blocker; keep the output citations-only.
- A module skipped without a reason is an unfinished pass.
