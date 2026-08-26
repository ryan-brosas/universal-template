# Repository selection quality bar

Use this gate before cloning a candidate into the inspiration library. It adapts the
pi-template foundation bar from:

- `project/pi-template/.pi/skills/pack-foundations/SKILL.md`
- `project/pi-template/.pi/skills/pack-foundations/foundations-workflow/references/quality-bar.md`
- `project/pi-template/.pi/skills/pack-foundations/foundations-workflow/references/workflow.md`
- `project/pi-template/scripts/run-inspo-tests.py`

The quality bar is evidence-based. Do not rank repositories by stars, LOC,
commit count, number of modules, or README polish.

## Five selection bars

| Bar | Required evidence | If missing |
|---|---|---|
| Relevance | A named DSH question or reusable capability the source can answer | skip or keep queued |
| Source/testability | Source paths are accessible and a direct test/check path is identified | inspect-only or queue with a reason |
| Provenance/license | Origin, ref, resolved commit, and license can be recorded; intended use is classified | pattern-only, inspect-only, or skip |
| Graph readiness | The canonical checkout can be represented by one ready Codebase Memory project in FULL mode | graph-blocked; do not claim indexed |
| Bounded scope | The useful seam can be studied one source at a time without copying the repository into notes | narrow the question or skip |

## Verdicts

- **accept** — all five bars are evidenced or an explicit, recorded exception is
  approved; proceed through clone → full index → catalog update.
- **maybe** — relevant, but a bar is unresolved; record the missing evidence in
  the queue and do not promote it to a foundation.
- **skip** — the source fails relevance, provenance, scope, or has a failed
  verification result; do not clone unless the user explicitly requests an
  inspect-only study.

A passing test suite is the strongest verification. Run the pi-template
`run-inspo-tests.py` harness where its repository-language rules apply. A
missing or unavailable runner may be recorded as a block with deterministic
source/retrieval probes, but it must never be reported as test-verified.

## Evidence record

Record the verdict and reason in `source.yml`, the queue or study note, and the
root `INSPO.md` catalog when the source is accepted. Keep the graph project
name, root, HEAD, FULL-mode status, generation/freshness, and exclusions next to
the pinned source. The graph selects seams; source and tests decide claims.

## Graph-only batch exception

An explicit user-authorized batch may refresh the FULL graph for existing pinned sources before their individual quality bars are complete. Record those sources as graph-indexed and queued or maybe; do not call them accepted, test-verified, license-approved, studied, or promoted. Every project still requires index_status ready plus canonical root and HEAD match, and every parse-partial, skipped, and intentional exclusion remains visible.
