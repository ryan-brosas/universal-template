---
name: milvus-foundation
description: "Use when porting Milvus-style background maintenance into your own system: segment allocation/sealing policies, L0 delete-log compaction eligibility, mix/clustering/sort compaction triggers, a hot-swappable prioritized task queue with per-channel type exclusion, crash-safe persisted task state machines, publish-before-retire meta mutations, target-based reconcilers, storage-format migrations under rate limits, or snapshot-protection gating of destructive rewrites. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."

---
# Milvus: Compaction & Segment Lifecycle Foundation

## Use this for
Use when porting Milvus-style background maintenance into your own system: segment allocation/sealing policies, L0 delete-log compaction eligibility, mix/clustering/sort compaction triggers, a hot-swappable prioritized task queue with per-channel type exclusion, crash-safe persisted task state machines, publish-before-retire meta mutations, target-based reconcilers, storage-format migrations under rate limits, or snapshot-protection gating of destructive rewrites. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/compaction-scheduler-type-exclusion.md` — drain one shared priority queue while five exclusion sets keep incompatible task types off the same channel.
- `references/compaction-queue-hot-prioritizer.md` — swap a live priority function by config name; same-name syncs are O(1) no-ops.
- `references/persisted-task-state-machine.md` — pipelining→executing→meta_saved→completed ladder where every transition persists before publishing.
- `references/task-admission-compacting-cas.md` — atomic check-and-set on all input segments plus synchronous unwind on every later failure.
- `references/plan-build-worker-refusal-retry.md` — build the wire plan; treat DataNode slot refusal as demotion-to-pending, not error.
- `references/slot-capacity-node-assignment.md` — dual-sentinel unassigned detection; restart restores executing tasks directly, pending ones through the queue.
- `references/l0-delete-compaction-eligibility.md` — an L0 segment merges only when its delete position precedes the earliest growing insert; Sealed targets fail fast.
- `references/l0-trigger-activity-cache.md` — write-refreshed active-collection cache demotes after 3 quiet reads past 3 trigger intervals.
- `references/l0-view-trigger-thresholds.md` — min-count/min-size trigger ladder with max-bounded greedy picking; first segment always taken.
- `references/l0-fast-finish-empty-result.md` — zero targets and empty outputs are success paths, never errors.
- `references/single-segment-delta-trigger.md` — three OR'd delete-pressure thresholds (file count / row ratio / byte size) pick single-segment rewrites.
- `references/clustering-trigger-policy.md` — version-aware min/max-interval ladder over partition stats; output rows derived from observed row width.
- `references/storage-version-upgrade-policy.md` — fleet-min semver gate + token bucket + TEXT-field downgrade refusal for format migration.
- `references/target-reconciler-convergence.md` — stateless satisfaction predicate drives declarative targets; blockers keep targets active, not satisfied.
- `references/target-state-machine-manual-rewrite.md` — intent-tagged desired-state records with idempotent ACTIVE→INACTIVE transitions.
- `references/manual-compaction-routing.md` — one API, four modes: flag-priority routing over force-merge/L0/clustering/rewrite-target.
- `references/force-merge-memory-budget.md` — live topology query (replicas, embedded nodes excluded, pooling fallback) sizes merge-all plans.
- `references/trigger-manager-ticker-lattice.md` — six tickers gate compute behind enable+capacity checks; sort compaction stays event-driven.
- `references/trigger-policy-registry.md` — construction-time policy map where optional registration IS feature enablement.
- `references/trigger-id-allocation-event-typing.md` — fresh round IDs make per-round status queries and single-flight checks possible.
- `references/coordinator-loop-wiring.md` — fast control loop and slow GC loop compose; state advance precedes scheduling precedes cleanup.
- `references/completion-meta-mutation-ordering.md` — AddSegment-before-AlterSegment inside one transactional action list; metrics commit after persistence.
- `references/fallback-position-inheritance.md` — merged segments derive positions from own logs with input-wide fallbacks.
- `references/persisted-taskmeta-reload-compat.md` — type-scoped upgrade shims mark pre-upgrade tasks failed without failing exempt types.
- `references/task-gc-summary-accounting.md` — cleaned-state drop after tolerance window; ten internal states roll up into two public ones.
- `references/binlog-id-prealloc-slot-pricing.md` — expansion-factor ID ranges avoid mid-compaction exhaustion; slots priced flat or by size.
- `references/segment-allocation-seal-policies.md` — pending-inclusive row accounting for inserts; four segment seal policies then two channel seal policies.
- `references/segmentview-projection-semantics.md` — read-only SegmentView snapshots where NumOfRows means DELETE count for L0 segments.
- `references/chanpart-grouping-predicates.md` — shared enumeration helper with per-policy level predicates composes every candidate scan.
- `references/bump-schema-stats-slot.md` — schema-evolution rides the full rewrite pipeline; stats tasks price slots by input size.
- `references/snapshot-protection-compaction-gates.md` — protection consults at trigger/admission/completion/reconciliation; L0 deliberately exempt at all four.

## Capsule map
- **Scheduling core** — `compaction-scheduler-type-exclusion`, `compaction-queue-hot-prioritizer`, `trigger-manager-ticker-lattice`, `trigger-policy-registry`, `coordinator-loop-wiring`: one mutex'd heap queue, name-keyed prioritizer sync, five-set exclusion lattice, capacity-gated policy ticks.
- **Task lifecycle** — `persisted-task-state-machine`, `task-admission-compacting-cas`, `plan-build-worker-refusal-retry`, `slot-capacity-node-assignment`, `task-gc-summary-accounting`, `persisted-taskmeta-reload-compat`: persist-before-publish state machines, CAS admission, refusal-as-demotion, delayed best-effort GC.
- **L0 delete plane** — `l0-delete-compaction-eligibility`, `l0-trigger-activity-cache`, `l0-view-trigger-thresholds`, `l0-fast-finish-empty-result`: position-cutoff eligibility, activity-cache prioritization, bounded greedy picks, empty-is-success.
- **Policy family** — `single-segment-delta-trigger`, `clustering-trigger-policy`, `storage-version-upgrade-policy`, `target-reconciler-convergence`, `target-state-machine-manual-rewrite`, `manual-compaction-routing`, `force-merge-memory-budget`, `trigger-id-allocation-event-typing`: delete-pressure, layout, format, and declarative-target triggers sharing typed events and round IDs.
- **Meta correctness** — `completion-meta-mutation-ordering`, `fallback-position-inheritance`, `snapshot-protection-compaction-gates`: publish-before-retire transactions, checkpoint inheritance, four-gate snapshot revalidation with L0 exemption.
- **Segment plane** — `binlog-id-prealloc-slot-pricing`, `segment-allocation-seal-policies`, `segmentview-projection-semantics`, `chanpart-grouping-predicates`, `bump-schema-stats-slot`: allocation accounting, seal stacks, view projections, group enumeration, metadata-only variants.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Natural next seams live worker-side (`internal/datanode/compactor/mix_compactor.go`) and in streaming (`internal/streamingnode` WAL), both outside this pass's datacoord scope.

## Provenance
Milvus (Apache-2.0), `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory project `ext-milvus` (`/mnt/hdd/utopia/inspo/external/milvus`, ready, 101,637n/1,079,739e, generation 2026-08-23T09:44:23Z, generation_matches=true, head==base zero drift). parse_partial ×182 are CI/build/C++ files — none cited. Skipped ×13 quarantined-after-crash incl. `garbage_collector_test.go` (read directly where needed). All 30 cited paths returned `no_recorded_issue`+`metadata_match` via check_index_coverage stdin-JSON.

## Full view (memory graph)
Revalidate `ext-milvus` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph note: BM25 retrieval works well here (Function/Method nodes carry tokens); use single-positional-JSON CLI form (`search_graph '{"project":"ext-milvus","query":"...","detail":"ids"}'`). Runner caveat: upstream Go tests require cgo (`milvus_core` C++ lib); CGO_ENABLED=0 breaks kafka imports — behavior evidence in capsules is direct-source reading plus upstream test files read at pin, honestly labeled per capsule.

## Boundaries
Adopt the scheduling/state-machine/meta-ordering contracts — they encode crash-safety and fairness invariants that survive any storage engine. Adapt thresholds, slot pricing, level taxonomy, and config plumbing to your host. Omit milvus product surfaces (gRPC APIs, proxy/querynode internals, cgo segcore, deployments/tests infra) and the datanode-side compaction EXECUTION engines (this pass owns the coordinator/datacoord control plane only).
