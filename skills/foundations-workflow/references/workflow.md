# Graph-first foundation runbook

This runbook minimizes repository reading while keeping source as the final authority.

## 1. Establish live graph state

Call `codebase-memory.list_projects`, then `codebase-memory.index_status({ project, verbose: true })`. Record:

- canonical project name and root;
- branch and HEAD SHA;
- index mode and generation;
- node/edge counts;
- parse-partial, skipped, and deliberately excluded scopes.

If the project is missing or stale, index/re-index before drawing structural conclusions. Do not create a duplicate project name.

**Gate:** one canonical, ready index whose root and commit match the source being cited.

## 2. Survey cheaply

1. `get_architecture` with only the needed aspects: overview, entry points, hotspots, boundaries, or clusters.
2. `search_graph` in compact/tree mode with a small limit. Use `detail: "ids"` for wide discovery and request signatures only for finalists.
3. Page while `has_more` is true, or narrow by file/label/query. Never treat the first page as exhaustive.
4. Use `query_graph` only for an aggregation or multi-hop question that search cannot answer.

Crown a primitive when it is reusable and its relationships explain why it matters. Fan-in is evidence, not the decision. Sweep repeatedly: high-seam modules (auth, audits) can support many capsules; small modules may warrant one. The repo is exhausted when, module by module, no new reusable seam remains — not at a fixed candidate count.

## 3. Trace contracts, not files

For each candidate:

1. Resolve its exact qualified name with `search_graph`.
2. Run `trace_path` inbound/outbound at the smallest useful depth. Request resolution evidence when a critical edge is heuristic.
3. Fetch the symbol with `get_code_snippet`.
4. Run `check_index_coverage` for every source and test path you intend to cite.

Escalate source access in this order:

- exact graph snippet;
- bounded source range around a clipped symbol;
- neighboring symbols required to explain the state transition;
- full file only when the contract genuinely spans the file and the reason is recorded.

For excluded tests, use `search_code`/direct grep to find test declarations, then read only the exact test blocks that pin the claim. An excluded test can be valid evidence, but it is source evidence—not a graph edge.

**Gate:** each claim has a symbol/path anchor, coverage status, and named probe. Unsupported candidates are omitted.

## 4. Decide adopt, adapt, or omit

- **Adopt** when the primitive's assumptions match the target.
- **Adapt** when the invariant transfers but APIs, providers, storage, or concurrency differ.
- **Omit** when the behavior is bespoke, untested, inaccessible, or cheaper to derive locally.

Record the reason, not just the verdict. This is the reusable decision future agents need.

## 5. Pressure-test the skill

Use one realistic scenario and a fixed rubric:

- chose the right primitive;
- named the exact source symbol;
- preserved the tested invariant;
- checked graph coverage/freshness;
- avoided loading irrelevant references.

Run RED without the new guidance. After authoring, run GREEN with the skill and an adversarial variant. If no agent runner is available, record the infrastructure block and run deterministic retrieval/content probes; do not invent a pass.

## 5b. Squeeze to the reusable bar
When the goal is promoting or re-engineering a foundation to the pack's capability/source-map quality bar, run the numbered squeeze, not a one-shot write. Load `references/squeeze-process.md`, prewalk the live index, crown seams module-by-module, author one capsule-vN reference per porting question, keep the leaf a lean routing surface, and record waves, module status, and RED/GREEN evidence only in the durable work record. Directly inspect the structural contract: Capsule map parity, extension recipe, graph provenance, capsule-v2 headings, source/test anchors, and the final diff.

## 6. Write the minimum durable artifact per seam
The leaf skill is a routing surface plus a capability/source map. Group its catalogued capsules by subsystem, then end with a compact recipe for adding a new capsule. Reference length follows the contract's complexity; no document-count or line-count target exists. Mine in waves only as an execution convenience: wave timing and module coverage belong in the durable work record, never the leaf skill.

Stop when every skill line is actionable and evidenced. Put unresolved areas in the durable work record instead of expanding prose. A repo is finished when that record shows every module mined or skipped-with-reason — never at a token or document budget.

## 7. Wire and verify

For new membership, follow `wiring-verification.md`. For a rewrite with unchanged membership, leave packs and manifest untouched. Always finish by recording direct graph, source, test, coverage, map-parity, and diff evidence in the work record.
