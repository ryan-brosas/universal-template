---
name: memory-graph-skill-miner
description: Mine indexed Codebase Memory repositories into verified foundation skills.
---

# Memory-Graph Skill Miner

This is the DSH adapter for the proven Hermes memory-graph mining process. It turns
one already-organized, indexed inspiration repository into a reusable foundation
leaf made of source-confirmed capsule references. The graph is the map; source and
direct tests are the authority. Do not invent a parallel note format or copy a
repository into the skill.

## When to Use

- Turn one ready Codebase Memory project into a foundation leaf.
- Re-enter an existing foundation for a deeper pass and new capsules.
- Run one dedicated Factory learning lane with a pinned target repository.
- Repair a foundation's capsule, loader, map, provenance, or verification parity.

Do not use for organizing or cloning inspo folders; use repo-inspo-organizer. Do not
use for batch graph reindexing, active DSH implementation, generic skill authoring,
or porting a known primitive; use the matching foundation leaf instead.

## Prerequisites

- The source checkout already exists in the established work/inspo library and is
  not a newly-created Git worktree.
- The target source, graph project, foundation leaf, and current pin are explicit.
  On-demand runs may select one target from the learning ledger, but never a script.
- The canonical workflow is available at
  /home/utopia/.dsh/skills/foundations-workflow/SKILL.md. Load it first, then load
  only the runbook references needed for the current gate.
- The canonical leaf and capsule templates are available at
  /home/utopia/.dsh/template/work/project/foundation-skill.md and
  /home/utopia/.dsh/template/work/project/foundation-capsule.md.
- A direct source check or test path is known, or its absence is recorded as a
  blocker. A missing runner is never a passing runner.

### Durable work-record layout

The canonical mining staging root is `/mnt/hdd/utopia/inspo/.skill-mining-work/`.
Each source record lives at `.skill-mining-work/<source-slug>/{state,research,verification}.md`;
the shared ledger lives at `.skill-mining-work/llm-repo-learning.md`. The layout migration
is complete; legacy `<source-slug>-work` siblings are not canonical and must not be recreated.
Collision-preserving originals are archived under `/mnt/hdd/utopia/archive/skill-mining-legacy-20260826/`.
Never create new sibling work directories beside source checkouts.

## How to Run

### On demand

1. Read the source's work/state.md, research.md, and verification.md plus the local
   learning ledger before choosing a seam.
2. Run the seven-gate procedure below for one source and one porting question at a
   time.
3. Persist the capsule, leaf map, verification evidence, and next-pass targets before
   yielding. Do not start a second repository in the same run.

### Factory continuation

Use a DSH Factory lane for autonomous continuation, but make each invocation a
Hermes-style learning-and-production batch rather than a one-seam tick. Configure
mining tasks with the native `standard` Agent preset, never `fabric` or `code`:
code-mode's generated `run_code` programs encourage batched shortcuts instead of
manual evidence-by-evidence study. Do not delegate mining to subagents or workflows.
The task prompt must include one dedicated lane, one target checkout, one graph
project, one target leaf, the inspected pin, current capsule counts, coverage caveats,
and an explicit allowed-file list. Use references/factory-lane-prompt.md as the prompt
skeleton. A batch must first write a durable learning note, then produce 5–8
distinct source-confirmed capsule-v2 outcomes (target six), refactor overlapping or
stale leaf material when warranted, run the gates, and update the ledger/work record
before it reports success. Never pad the batch with invented or duplicate capsules;
if fewer than five genuinely uncited/refactorable seams remain, prove closure or
record the blocker and remaining targets.

## Quick Reference

- Canonical process: foundations-workflow, then its graph-rules, quality-bar,
  squeeze-process, and wiring-verification references as needed.
- Graph discovery: mcp__codebase-memory__list_projects,
  mcp__codebase-memory__index_status, mcp__codebase-memory__get_architecture,
  mcp__codebase-memory__search_graph, mcp__codebase-memory__trace_path,
  mcp__codebase-memory__get_code_snippet, and
  mcp__codebase-memory__check_index_coverage.
- Complex graph queries: mcp__codebase-memory__query_graph only when search and
  traces cannot answer the question.
- Durable records: .skill-mining-work/source-slug/state.md, research.md, verification.md, and
  the local inspo/.skill-mining-work/llm-repo-learning.md ledger.
- Output: the target foundation leaf's SKILL.md and references/*.md only, plus the
  leaf's new-membership wiring when it is genuinely new.
- Core loop: graph map -> source/test confirmation -> capsule-v2 -> pressure test ->
  leaf/map parity -> durable state.

## DSH Translation of the Hermes Process

Hermes used OpenViking as a second learning ledger and committed from a shared
Pi-template checkout. DSH replaces those surfaces as follows:

| Hermes surface | DSH surface |
|---|---|
| OpenViking llm-repo-learning resource | inspo/.skill-mining-work/llm-repo-learning.md plus each source work record |
| foundations-workflow in Pi-template | /home/utopia/.dsh/skills/foundations-workflow |
| Pi foundation templates | /home/utopia/.dsh/template/foundation-*.md |
| codebase-memory CLI | native, individual Codebase Memory MCP tool calls |
| Hermes cron | DSH Factory recurring task |
| skill_manage / Pi file tools | DSH write, edit, read, grep, bash, and the target skill path |
| shared Pi checkout commit | explicit DSH file writes; commit only if the target is actually Git-managed |

Do not call OpenViking, write Pi-specific paths, or create a second inspo tree from
this skill. The local learning ledger is the durable scheduling surface: if it is
not updated, the pass is incomplete.

## Durable State Contract

The local ledger is the DSH analogue of Hermes llm-repo-learning. Keep one row per
source with, at minimum:

    source | foundation leaf | graph project | pin | pass | refs | v2 refs |
    last pass | next-pass targets | blockers

Every run must also leave a source work-record entry containing a learning note
written before production edits, followed by the production outcome:

- the pass number and exact graph project/root/branch/HEAD/mode/counts;
- modules or seams mined during this run;
- modules or seams omitted with a reason;
- direct source/test/coverage evidence and honest runner blocks;
- the exact leaf files changed and capsule/map parity result;
- concrete NEXT-PASS TARGETS, not a generic “continue deeper”;
- a timestamped completion marker or the run's explicit blocked state.

Read the ledger and work record immediately before editing. Compose shared-ledger
changes in a scratch value, then re-read the target before writing. If a side effect
or write result is uncertain, inspect the file and Factory/Fabric state before
retrying. Never rely on conversational memory for the resume position.

## Procedure

1. **Load the canonical workflow.** Read foundations-workflow/SKILL.md and the
   references required for the current gate. Do not create a second capsule format.
   Completion: the current run names its source, target leaf, and active porting
   question.

2. **Establish one lane.** Resolve the source's canonical checkout and user-facing
   alias, confirm it is the existing inspo checkout, and read its source card and
   work record. Read the learning-ledger row. A dedicated Factory lane owns only its
   named source, leaf, work-record row, and explicitly allowed wiring lines.
   Completion: sibling lanes and forbidden paths are recorded.

3. **Gate 1 — live graph.** Call list_projects, then index_status for the named
   project with verbose true. Record root, branch, HEAD, mode, generation, node and
   edge counts, freshness, parse-partial files, skipped files, and intentional
   exclusions. Require the graph root and HEAD to match the source being cited.
   If the project is missing or stale, re-index only this existing checkout in FULL
   mode and re-run index_status. Never batch-index or create a duplicate project
   name in a mining run.
   Completion: one canonical ready graph or an explicit blocked record.

4. **Gate 2 — graph-led seam selection.** Use get_architecture with only needed
   aspects, then search_graph in ids/default mode with a narrow query, file pattern,
   label, or relationship. Page while has_more is true. Use trace_path inbound and
   outbound to understand ownership and call/data-flow boundaries. Use semantic or
   similar relationships only as discovery evidence. The graph selects connected
   candidates; it does not prove behavior.
   Completion: one reusable seam and one precise porter question are named.

5. **Gate 3 — source and test confirmation.** Resolve the exact qualified symbol with
   search_graph, trace its smallest useful neighborhood, fetch it with
   get_code_snippet, and call check_index_coverage for every source and test path to
   cite. Read the decisive source range and direct test with DSH file tools. Source
   wins over graph output. Inspect error, recovery, configuration, shutdown, and
   test-fixture paths when they define the invariant.
   Completion: the claim has a path/symbol anchor, coverage status, and named probe.

6. **Gate 4 — author the production batch.** Copy the canonical shape from
   foundation-capsule.md into the target leaf's references directory. After the
   learning note, answer 5–8 distinct porting questions in the same bounded run
   (target six), one capsule-v2 per question, each with Source, Path/Symbol,
   Signature, Data Shape, a minimal labelled Decisive source excerpt, Flow,
   Invariant, Probe, live Retrieve call, and Adopt/Adapt/Omit Verdict. A substantive
   refactor/merge of an existing capsule may count as one outcome only when it is
   source-confirmed and closes a real coverage gap; never duplicate an existing
   reference. Update the leaf loader and Capsule map in the same bounded change.
   Do not vendor modules or turn graph output into a repository summary.
   Completion: the batch has 5–8 durable, source-confirmed outcomes, or the run
   records an evidenced fewer-than-five closure/blocker; every loader/map entry
   resolves to exactly one file.

7. **Depth-first learning squeeze.** Before selecting the batch, compare the ledger,
   state.md, research.md, verification.md, current SKILL.md, and reference map. Mark
   each candidate covered, partial, or uncited; refactor partial coverage instead of
   creating duplicates. Study one connected subsystem deeply, then continue module by
   module until the batch target is met or the source is demonstrably exhausted for
   this pass. Record omitted-with-reason for every deferred subsystem. Large
   repositories need multiple passes; each pass starts from concrete NEXT-PASS TARGETS
   and must leave a better mental model plus durable production artifacts.
   Completion: learning note, batch refs/refactors, parity evidence, and next targets
   all agree.

8. **Gate 5 — behavior pressure test.** Run RED without the new capsule and GREEN
   with it against a realistic porting scenario, including an adversarial retrieval.
   Check the right primitive, exact retrieval target, preserved invariant, direct
   probe, and absence of irrelevant loading. GREEN must pass the canonical bar twice
   when an agent runner exists. If no runner exists, record the infrastructure block
   and run deterministic retrieval/content/probe checks; never fabricate a pass.
   Completion: observed pass evidence or an explicit blocked result.

9. **Gate 6 — wire only when membership is new.** For an existing leaf, do not touch
   the pack router or catalog membership. For a genuinely new DSH foundation leaf,
   add it under /home/utopia/.dsh/skills/<leaf>/ and verify the filesystem catalog
   discovers it. DSH has
   no Pi packs.json or manifest surface here; do not invent or edit those files.
   Completion: membership is unchanged or the new leaf/router line is parity-checked.

10. **Gate 7 — verify and persist.** Re-run the capsule/map/disk parity checks, every
    cited graph retrieval, source/test probe, and coverage check. Inspect the final
    diff and ensure no forbidden path changed. Update the leaf provenance and full
    graph view when source pin or counts changed. Update the source work record and
    llm-repo-learning.md row with pass, refs, v2 count, modules, blockers, and concrete
    NEXT-PASS TARGETS. The ledger update is part of the deliverable, not housekeeping.
    Completion: direct graph, source, test, coverage, parity, diff, and durable-state
    evidence are recorded.

## Lane File Boundary

A scheduled mining lane may modify only:

- the named foundation leaf and its references;
- the named source's work/state.md, research.md, and verification.md;
- the named source row and next-pass text in inspo/.skill-mining-work/llm-repo-learning.md;
- its own new-membership leaf under ~/.dsh/skills/, only when needed.

Everything else is read-only. Never edit the source checkout, repo-inspo-organizer,
INSPO.md, QUEUE.md, another leaf, another lane's ledger row, or an active DSH project
from a mining lane. If the current files use a different established layout, record
the resolved paths in the lane prompt before writing; do not silently create aliases.

## Doubled Manual-Learning Enforcement

This rule exists in both this skill and every Factory task prompt. Neither copy may
weaken the other. A run must pass both checkpoints:

1. **Preflight:** confirm the Agent preset is `standard`, name exactly one repository
   and connected subsystem, and state that discovery will use native individual
   Codebase Memory MCP calls. If the preset exposes only code-mode/`run_code`, stop
   blocked instead of beginning exploration.
2. **Completion:** enumerate each seam's explicit graph search, trace, snippet,
   coverage check, decisive source read, direct test read, and manually authored file.
   Certify that no forbidden shortcut or delegation occurred. Any shortcut-tainted
   output is invalid: discard it and redo the evidence chain manually, or report the
   run partial/blocked.

## No-Script and Parallel-Lane Rules

- Never use `run_code`/code-mode programs, helper or generated scripts,
  Python/Node/Ruby/Perl one-liners, shell loops, heredocs, xargs/find pipelines,
  awk/sed/jq transforms, temporary automation, generated arrays of tool calls, or
  template-filled prose for selection, discovery, extraction, counting, probing,
  parity, batch editing, authoring, or verification.
- Do not delegate repository learning or capsule authoring to subagents or workflows.
  The assigned model must inspect, reason about, and author every seam itself.
- Use native individual MCP/file calls and manually write or edit each durable artifact.
  Shell is allowed only for an existing repository-owned test/check command and exact
  git status/diff; it must not create files or discover/summarize source.
- Do not use git stash. If the target is Git-managed, stage only explicit owned paths,
  pull/rebase before push, and verify HEAD content rather than trusting commit stats.
- Shared ledger rows race. Re-read before writing, compose the append outside the
  shared file, re-grep after writing, and repair only your own row if it changed.
- A graph result, ready status, or missing runner is not behavioral proof.
- A parse-partial or skipped path must be cited as a coverage caveat and checked from
  source before relying on it.
- If a sibling may be mid-update, re-check the shared gate twice before editing; do
  not revert or “clean up” a transient orphan owned by another lane.
- If a run ends mid-exploration, persist learned facts and next targets even when no
  capsule is ready. Half-knowledge written down is better than lost progress.

## Pitfalls

- Treating the first search_graph page as exhaustive; honor total and has_more.
- Treating a stale graph twin or matching metadata as fresh content; verify a symbol
  introduced by the cited pin and compare the served source with the checkout.
- Citing a parse-partial file without reading its flagged range directly.
- Writing a plausible Probe or Retrieve command without executing it byte-for-byte.
- Counting path-form and basename-form citations as different references during parity.
- Updating a shared row with a stale whole-file replacement and deleting a sibling's
  entry; re-read and apply a scoped change.
- Expanding the leaf into a ledger; wave history and unresolved work belong in the
  work record.
- Marking a license, test, or runner as approved because the package metadata or graph
  says so. Preserve the blocker and keep reuse citations-only when necessary.
- Running a Factory lane without a target pin, allowed-file list, or next-pass target.
- Calling the current source complete because a capsule count target was reached.

## Verification

Before reporting a successful run, confirm all of the following:

- the source checkout, graph project, and cited HEAD match;
- graph coverage was checked for every cited source/test path;
- every new or rewritten reference is capsule-v2 and has an executed Probe and Retrieve;
- leaf loader, Capsule map, and reference files are bidirectionally parity-equal;
- RED/GREEN evidence is observed or the block is explicitly recorded;
- only lane-owned paths changed;
- the source work record and local learning-ledger row contain the pass, evidence,
  blockers, and concrete NEXT-PASS TARGETS.

A missing evidence item means the run is partial or blocked, not complete.

## References

- /home/utopia/.dsh/skills/foundations-workflow/SKILL.md — canonical seven-gate process.
- /home/utopia/.dsh/template/work/project/foundation-skill.md — canonical leaf structure.
- /home/utopia/.dsh/template/work/project/foundation-capsule.md — canonical capsule-v2 structure.
- references/factory-lane-prompt.md — dedicated Factory prompt and file boundary.
- references/durable-learning-ledger.md — local ledger row and resume contract.
