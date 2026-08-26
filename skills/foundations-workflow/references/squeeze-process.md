# Foundation squeeze process

A **squeeze** is the serial, wave-based mining of one indexed inspiration repo into implementation capsules. It is the Oh My Pi result — source-grounded capsules grouped by capability behind a routing surface — made repeatable. It is **not** a word-count or reference-count target.

## Entry gate

Load `foundations-workflow` and the packed router before touching an indexed repo. The router description decides the entry: mining/re-squeezing/migrating a repo routes to the workflow first; porting a known primitive routes to the matching leaf — never the workflow. When the intent is any foundation-authoring step, a `/skill:pack-foundations squeeze <repo>` invocation is the hard entry.

## Preconditions
- One canonical, ready Codebase Memory project: `list_projects`, then `index_status({ project, verbose: true })` and record project/root/branch/HEAD/mode/node+edge counts/exclusions/freshness in the durable work record.
- The source repo and its tests remain the authority; the graph is only a discovery index.
- No work on the next repo until the current one has a closed ledger row (see stop rule).

## Wave loop
Waves are an execution convenience, never a quota. One source repo at a time; within a wave, mine seam-by-seam:

```text
crown seam -> capsule-v2 reference -> update Capsule map -> record direct evidence -> commit
```

- Crown a seam when it is reusable and its relationships explain why it matters (fan-in is evidence, not the decision). Sweep a module until no new reusable seam remains, then move to the next module.
- Author one `<!-- capsule-v2 -->` reference per distinct porting question: Path/Symbol, Signature, Data Shape, Flow, Invariant, Probe, Retrieve. No line/reference/citation min or max.
- Group capsules in the leaf's **Capsule map** by subsystem; keep the leaf a lean routing surface, never a project ledger.
- Wave/module status, unresolved modules, adopt/adapt/omit verdicts, and RED/GREEN evidence live only in the durable work record, never the leaf.

## Stop criteria
The repo is squeezed when the work record rows every module as `mined`, `skipped-with-reason`, or `omitted` and every public skill line has retrieval provenance, a confirmed anchor, a behavior boundary, and an honest coverage note. Never stop at a token or document budget.

## RED/GREEN behavior pressure test
Score 5 bars (right foundation, relevant primitive, exact retrieval target/coverage, preserved invariant/probe, no irrelevant loading). RED without the capsule must expose a real miss; WITH it, GREEN passes 4/5 twice incl. adversarial. If no runner is available, record the block and run deterministic retrieval/content probes; **never** a fabricated pass. Record tool-call counts, cost, and exact copied invariants/symbols.

## Close
Before the ledger row closes, directly inspect capsule/map parity, provenance, the extension recipe, every cited graph/source/test path, and the final diff. Record the observed evidence and any blocked runner; do not substitute a fabricated pass.
