---
name: memory-graph-skill-miner
description: "Use when mining an indexed Codebase Memory repository into a verified foundation skill — the autonomous learn → note → capsule → OpenViking sync → close loop. Host-neutral: runs from any agent CLI (DSH Factory lane, pi recurring task, or manual invocation)."
---

# Memory-Graph Skill Miner

Host-neutral autonomous repo-learning loop. It turns one already-organized, indexed
inspiration repository into a reusable foundation leaf made of source-confirmed
capsule references, pushes every pass to OpenViking, and closes the repository when
nothing new remains to note. The graph is the map; source and direct tests are the
authority. Do not invent a parallel note format or copy a repository into the skill.

## Core Principle

The graph is the map; source and direct tests are the authority. One invocation owns
exactly ONE source row, writes the learning note FIRST, produces 5–8 source-confirmed
capsule-v2 outcomes per pass (target six), syncs every pass to OpenViking, and updates
the ledger row AND Status board line in the same write — closing only when no uncited
reusable seam remains.

## When to Use / NOT

- **Use when:** turning one ready Codebase Memory project into a foundation leaf;
  re-entering an existing foundation for a deeper pass; running a scheduled learning
  lane with a pinned target; repairing a foundation's capsule, loader, map,
  provenance, or verification parity.
- **NOT when:** organizing or cloning inspo folders (use repo-inspo-organizer); batch
  graph reindexing; generic skill authoring; porting a known primitive (load the
  matching foundation leaf instead).

## Workflow

One invocation runs the loop described in `The Loop` through the seven-gate `Procedure`
below: load the canonical workflow → establish one lane → Gate 1 live graph → Gate 2
graph-led seam selection → Gate 3 source and test confirmation → Gate 4 author the
production batch (with the depth-first squeeze before selection) → Gate 5 behavior
pressure test → Gate 6 wire only when membership is new → Gate 7 verify and persist.
Each gate has an explicit completion condition; the run ends with the ledger row,
Status board line, and work record updated — or an explicit blocked record.

## Prerequisites

- The source checkout already exists in the established inspo library and is not a
  newly-created Git worktree.
- The target source, graph project, foundation leaf, and current pin are explicit.
  On-demand runs may select one target from the learning ledger, but never by script.
- The canonical workflow is `~/.agents/skills/foundations-workflow/SKILL.md`. Load it
  first, then load only the runbook references needed for the current gate.
- The canonical templates are `~/.agents/templates/foundation-skill.md` and
  `~/.agents/templates/foundation-capsule.md`. Host mirrors (e.g.
  `/home/utopia/.dsh/template/work/project/foundation-*.md`) are derived copies; fix
  drift in `~/.agents`, never in a mirror.
- `~/.dsh/skills` is a **symlink** to `~/.agents/skills` — one physical catalog, not a
  copy. Writing to the canonical `~/.agents/skills/<slug>-foundation/` path IS the
  `.dsh` view; there is no separate skills mirror to keep in sync or copy back. If your
  capsule count differs from an earlier reading, that is your own cross-pass growth, NOT
  a "mirror divergence" — there is no second copy to drift from.
- A direct source check or test path is known, or its absence is recorded as a
  blocker. A missing runner is never a passing runner.

### Durable work-record layout

The canonical mining staging root is `/mnt/hdd/utopia/inspo/.skill-mining-work/`.
Each source record lives at `.skill-mining-work/<source-slug>/{state,research,verification}.md`;
the shared ledger lives at `.skill-mining-work/llm-repo-learning.md`. The layout migration
is complete; legacy `<source-slug>-work` siblings are not canonical and must not be recreated.
Collision-preserving originals are archived under `/mnt/hdd/utopia/archive/skill-mining-legacy-20260826/`.
Never create new sibling work directories beside source checkouts.

## The Loop (one invocation, any host)

1. Read the ledger, its Status board, and the source work record; own exactly ONE
   source row for this invocation.
2. Write the learning note FIRST (research.md): mental model, covered/partial/uncited
   seams, porter questions.
3. Run the seven-gate procedure below over one connected subsystem → 5–8
   source-confirmed capsule-v2 outcomes (target six), or an evidenced fewer-than-five
   closure/blocker.
4. OpenViking sync phase (below).
5. Update the ledger row AND the Status board line in the same write; persist concrete
   next-pass targets.
6. Closure: no uncited reusable seam left ⇒ status `complete` with closure evidence.
   Any HEAD advance past the pin ⇒ reopen to `active` with FULL re-index + diff-first
   re-adjudication before new citations.

## How to Run

### On demand

1. Read the source's work/state.md, research.md, and verification.md plus the local
   learning ledger before choosing a seam.
2. Run the seven-gate procedure below for one source and one porting question at a
   time.
3. Persist the capsule, leaf map, verification evidence, and next-pass targets before
   yielding. Do not start a second repository in the same run.

### Scheduled continuation (any host)

Each scheduled invocation is a learning-and-production batch, never a one-seam tick.
Do not delegate mining to subagents or workflows; the assigned model inspects, reasons
about, and authors every seam itself. The task prompt must include one dedicated lane,
one target checkout, one graph project, one target leaf, the inspected pin, current
capsule counts, coverage caveats, and an explicit allowed-file list.

Per-host drivers:

- **DSH Factory:** native `standard` Agent preset only (never `fabric`/`code` — code
  mode's generated programs enable exactly the batching shortcuts this lane forbids);
  prompt skeleton, deployment guard, and fleet bindings in
  `references/dsh-factory-lane.md`.
- **pi / other CLIs:** any recurring-task mechanism that can run this skill with the
  same prompt contract. Keep the writer topology of the driving host: one lane owns
  one repo, and shared-file writes follow the ledger discipline below.

Hard rule: a lane may write only its owned row/board line and owned files. Concurrent
lanes without a working lease surface cause lost updates on shared rows (documented
repeatedly in ledger history); if the host has no lease mechanism, serialize the lanes.

## Quick Reference

- Canonical process: foundations-workflow, then its graph-rules, quality-bar,
  squeeze-process, and wiring-verification references as needed.
- Graph discovery: Codebase Memory MCP tools — list_projects, index_status,
  get_architecture, search_graph, trace_path, get_code_snippet, check_index_coverage.
- Complex graph queries: query_graph only when search and traces cannot answer.
- Durable records: .skill-mining-work/<slug>/{state,research,verification}.md plus the
  llm-repo-learning.md ledger and its Status board.
- Output: the target foundation leaf's SKILL.md and references/*.md only. Catalog
  discovery is filesystem-based; no router or manifest wiring exists.
- Core loop: graph map -> source/test confirmation -> capsule-v2 -> pressure test ->
  leaf/map parity -> OpenViking sync -> durable state.

## Durable State Contract

The local ledger is the scheduling and resume surface. Keep one row per source with,
at minimum:

    source | foundation leaf | graph project | pin | pass | refs | v2 refs |
    last pass | next-pass targets | blockers

Keep the ledger's Status board in sync in the same write: one line per source with
status `active` / `complete` / `blocked`. `complete` only when next-pass targets are
empty AND the coverage matrix shows 0 uncited reusable seams (every omission recorded
with a reason); `blocked` when a standing blocker prevents closure; any HEAD advance
past the pin reopens a `complete` row to `active` with FULL re-index + diff-first
re-adjudication before new citations.

### OpenViking sync phase (once per pass, after production writes, before ledger update)

1. Push the pass's learning note, verification record, and new capsule files into
   `viking://resources/llm-repo-learning-passN-<slug>/` (stable repo slug, one
   resource dir per pass). Use whichever surface exists in this session, in order:
   - MCP tools `memadd`/`memfind`/`memread` if connected;
   - otherwise the `ov` CLI. It is NOT on the default PATH of subagent sessions —
     full path: `/home/utopia/.hermes/hermes-agent/venv/bin/ov`. Pattern:
     `ov add-resource <leaf>/references -p viking://resources/llm-repo-learning-passN-<slug> --wait --include "*.md"`
     then `ov add-resource <work-record>.md --to viking://resources/llm-repo-learning-passN-<slug>/<name>.md --wait`.
2. Verify with `memfind` or `ov find -n 10 "<a newly cited symbol>"` that at least one
   newly cited symbol is retrievable; record the probe in the work record. Hits are
   pointers, not proofs.
3. Both surfaces unreachable ⇒ record the degraded path in the work record and
   continue; the local ledger stays authoritative. Never block the pass on OpenViking.

OpenViking is the semantic search surface, never the scheduling surface: the local
ledger decides what happens next.

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
or write result is uncertain, inspect the file and host scheduler state before
retrying. Never rely on conversational memory for the resume position.

## Procedure

1. **Load the canonical workflow.** Read foundations-workflow/SKILL.md and the
   references required for the current gate. Do not create a second capsule format.
   Completion: the current run names its source, target leaf, and active porting
   question.

2. **Establish one lane.** Resolve the source's canonical checkout and user-facing
   alias, confirm it is the existing inspo checkout, and read its source card and
   work record. Read the learning-ledger row and Status board line. A dedicated lane
   owns only its named source, leaf, work-record row, and board line.
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
   cite. Read the decisive source range and direct test with the host's file tools.
   Source wins over graph output. Inspect error, recovery, configuration, shutdown,
   and test-fixture paths when they define the invariant.
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

9. **Gate 6 — wire only when membership is new.** For an existing leaf, touch nothing
   else in the catalog. For a genuinely new leaf, create it under the shared catalog
   (`~/.agents/skills/<leaf>/`, or the host's catalog root when the deployment keeps
   leaves elsewhere) and verify filesystem discovery. No manifest or router files
   exist; do not invent or edit them.
   Completion: membership is unchanged or the new leaf is discovered by the host.

10. **Gate 7 — verify and persist.** Re-run the capsule/map/disk parity checks, every
    cited graph retrieval, source/test probe, and coverage check. Inspect the final
    diff and ensure no forbidden path changed. Update the leaf provenance and full
    graph view when source pin or counts changed. Update the source work record, the
    llm-repo-learning.md row, and the Status board line with pass, refs, v2 count,
    modules, blockers, and concrete NEXT-PASS TARGETS. The ledger update is part of
    the deliverable, not housekeeping.
    Completion: direct graph, source, test, coverage, parity, diff, and durable-state
    evidence are recorded.

## Lane File Boundary

A scheduled mining lane may modify only:

- the named foundation leaf and its references;
- the named source's work/state.md, research.md, and verification.md;
- the named source row and Status board line in inspo/.skill-mining-work/llm-repo-learning.md;
- its own genuinely-new leaf under the shared catalog, only when needed.

Everything else is read-only. Never edit the source checkout, repo-inspo-organizer,
INSPO.md, QUEUE.md, another leaf, another lane's ledger row or board line, or an
active project of the driving CLI from a mining lane. If the current files use a
different established layout, record the resolved paths in the lane prompt before
writing; do not silently create aliases.

## Manual-Learning Enforcement

This rule exists in both this skill and every scheduled task prompt. Neither copy may
weaken the other. A run must pass both checkpoints:

1. **Preflight:** name exactly one repository and connected subsystem, and state that
   discovery will use individual Codebase Memory MCP calls. If the host preset exposes
   only code-generation mode, stop blocked instead of beginning exploration.
2. **Completion:** enumerate each seam's explicit graph search, trace, snippet,
   coverage check, decisive source read, direct test read, and manually authored file.
   Certify that no forbidden shortcut or delegation occurred. Any shortcut-tainted
   output is invalid: discard it and redo the evidence chain manually, or report the
   run partial/blocked.

## No-Script and Parallel-Lane Rules

- Never use code-generation-mode programs (e.g. `run_code`), helper or generated
  scripts, Python/Node/Ruby/Perl one-liners, shell loops, heredocs, xargs/find
  pipelines, awk/sed/jq transforms, temporary automation, generated arrays of tool
  calls, or template-filled prose for selection, discovery, extraction, counting,
  probing, parity, batch editing, authoring, or verification.
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
- Running a scheduled lane without a target pin, allowed-file list, or next-pass target.
- Calling the current source complete because a capsule count target was reached.

## Red Flags

The full list is in `Pitfalls` above; the hard ones: treating a graph result, ready
status, or missing runner as behavioral proof; writing a plausible Probe or Retrieve
command without executing it byte-for-byte; updating a shared ledger row with a stale
whole-file replacement that deletes a sibling's entry; expanding the leaf into a ledger;
and calling the current source complete because a capsule count target was reached.

## Verification

Before reporting a successful run, confirm all of the following:

- the source checkout, graph project, and cited HEAD match;
- graph coverage was checked for every cited source/test path;
- every new or rewritten reference is capsule-v2 and has an executed Probe and Retrieve;
- leaf loader, Capsule map, and reference files are bidirectionally parity-equal;
- RED/GREEN evidence is observed or the block is explicitly recorded;
- only lane-owned paths changed;
- the source work record, local learning-ledger row, and Status board line contain the
  pass, evidence, blockers, and concrete NEXT-PASS TARGETS.

A missing evidence item means the run is partial or blocked, not complete.

## Skill Result Contract

```
<skill_result>
  <skill><name></skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References

- `~/.agents/skills/foundations-workflow/SKILL.md` — canonical seven-gate process.
- `~/.agents/templates/foundation-skill.md` — canonical leaf structure.
- `~/.agents/templates/foundation-capsule.md` — canonical capsule-v2 structure.
- `references/durable-learning-ledger.md` — ledger row, Status board, and resume contract.
- `references/dsh-factory-lane.md` — DSH Factory host adapter: preset rules, prompt skeleton, deployment guard, fleet bindings.
