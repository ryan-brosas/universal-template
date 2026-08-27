---
name: cognee-foundation
description: "Use when building or porting cognee-style knowledge-pipeline memory engines — dataset-scale task-run engines with rollback, deterministic DataPoint identity, exact-reconstruction chunkers, ontology-canonicalized graph construction, provenance-folded writes, vector-to-graph triplet ranking, hybrid RRF retrieval lanes, and additive contradiction handling. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# cognee: Knowledge-Pipeline Memory Engine Foundation

## Use this for
Use when building or porting LLM memory/knowledge-graph pipelines: dataset-scale task-run engines with rollback, deterministic DataPoint identity, exact-reconstruction chunkers, ontology-canonicalized graph construction, provenance-folded writes, vector-to-graph triplet ranking, hybrid RRF retrieval lanes, and additive contradiction handling. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/route-resolver-explicit-mapping.md` — Which task list does one data item run? Pure router + fail-loud KeyError on unmapped routes.
- `references/task-engine-four-callable-shapes.md` — How do coroutine/function/generator/async-generator tasks stream through one batched contract?
- `references/recursive-task-chain-provenance.md` — Why does the chain recurse per result, and what does first-writer-wins stamping pin?
- `references/dataset-run-engine-semaphore.md` — Per-item concurrency under one run lifecycle; flush-before-terminal-event ordering.
- `references/incremental-item-skip-marker.md` — Content-hash completion markers and why rollback excludes AlreadyCompleted items.
- `references/rollback-artifact-first-ordering.md` — Graph/vector artifacts die before relational ownership rows; stale-run recovery rules.
- `references/background-task-anchoring.md` — Strong refs or the GC silently eats fire-and-forget pipeline runs.
- `references/reentrant-dataset-lock.md` — ContextVar held-set gives re-entrancy over a plain asyncio.Lock.
- `references/datapoint-deterministic-identity.md` — uuid5 over class-namespaced identity_fields; id_for as single source of truth.
- `references/chunk-ladder-exact-reconstruction.md` — word→sentence→paragraph tokens whose join reproduces the input exactly.
- `references/same-name-entity-disambiguation.md` — Name-based merge ids plus chunk-scoped ordinals on collision.
- `references/ontology-preconstruction-canonicalization.md` — Match and collapse onto the ontology BEFORE graph construction.
- `references/datapoint-graph-walker-model-cache.md` — Model fields become nodes/edges; bounded class cache fixes a 50MB/cycle pydantic leak.
- `references/provenance-folded-writes.md` — Atomic source-ref folding (non-hybrid) vs attach-pass (hybrid); ledger-before-write.
- `references/triplet-ranking-penalty-semantics.md` — Penalty defaults are "no information"; blend only real cosine distances.
- `references/hybrid-rrf-chunk-summary-fusion.md` — RRF over chunk+summary pairs; importance/truth/personal factors compose fail-open.
- `references/hybrid-entity-fact-lanes.md` — 1-hop bullets, tiered ordering, budget hand-off between entity and fact lanes.
- `references/hybrid-deferral-ladder.md` — Hard-error knobs vs soft-defer capabilities for HYBRID_COMPLETION.
- `references/contradiction-detection-additive-edges.md` — Touched-region facts in, `contradicts` edges out, nothing deleted.
- `references/functional-supersession-recency.md` — Declared single-valued relations supersede by recency; history tagged not deleted.
- `references/edge-to-text-rendering.md` — Stable bracket-label markup with edge_text as suffix; fenced node blocks.
- `references/search-fanout-facade.md` — Dataset fan-out with per-dataset context and backwards-compatible result shapes.
- `references/chunk-associations-propose-verify.md` — Vector candidates propose, LLM verdicts dispose, sorted pairs dedup.
- `references/dry-run-cost-estimator.md` — Token/cost forecast sharing the execution router, side-effect free.
- `references/session-turn-arbitration.md` — should-answer gate BEFORE retrieval; answer-grounded evidence appends.
- `references/pipeline-qualification-gate.md` — Dataset status short-circuits are optimization, never the safety mechanism.
- `references/vector-search-fan-shapes.md` — Per-collection gather with structurally valid empties for missing collections.
- `references/dlt-deterministic-route.md` — LLM-free ingestion for structured sources: purge-and-replace on stable ids.
- `references/code-route-dual-granularity.md` — Repo vs file code routes feeding shared storage.
- `references/global-context-index-buckets.md` — Bucketed global summaries prepended additively to any retriever.
- `references/feedback-importance-weights.md` — Weights ride DataPoints; flag-off must be byte-identical rankings.
- `references/rdf-export-uri-preservation.md` — Keep external IRIs end-to-end or open-world linking dies.
- `references/unified-engine-capabilities.md` — Capability flags pick hybrid/graph-only/split write shapes.
- `references/session-distillation-graph.md` — Conversations re-enter the STANDARD pipeline as DataPoints.
- `references/dataset-deletion-slug-protection.md` — Delete only slugs losing their last dataset anchor.
- `references/merge-results-conversational-reserve.md` — Identity-deduped fusion reserving a minority slice for history.

## Capsule map
- **Cognify routing** — `route-resolver-explicit-mapping`: pure per-item route resolver; explicit table; KeyError beats silent LLM fallback.
- **Task engine** — `task-engine-four-callable-shapes`: type-dispatched executors; generator tasks yield batches, coroutines yield items; _Drop/enriches.
- **Chain core** — `recursive-task-chain-provenance`: recursion per result; next-task batch-size handshake; visited-set provenance stamping.
- **Run engine** — `dataset-run-engine-semaphore`: semaphore(data_per_batch), per-item copied extras, one lifecycle, flush-before-complete.
- **Incremental skip** — `incremental-item-skip-marker`: hash-keyed status marker; AlreadyCompleted excluded from rollback targets.
- **Rollback** — `rollback-artifact-first-ordering`: delete artifacts then ownership rows; shared-slug guard; STARTED-only stale recovery.
- **Background anchoring** — `background-task-anchoring`: module-set strong refs + done-callback self-discard.
- **Dataset lock** — `reentrant-dataset-lock`: ContextVar held-set marks held-while-body-advances, reset before each yield.
- **Node identity** — `datapoint-deterministic-identity`: uuid5(f"{cls}:{normalized values}"); opt-in identity_fields; MRO-drop warning.
- **Chunking** — `chunk-ladder-exact-reconstruction`: whitespace-with-word tokens; content-derived uuid5 chunk ids; overlap tail carry.
- **Entity dedup** — `same-name-entity-disambiguation`: name-based id default; (name, chunk.id, ordinal) collision fallback.
- **Ontology** — `ontology-preconstruction-canonicalization`: canonicalize → collapse survivors → re-point edges → ordinary construction.
- **Graph walker** — `datapoint-graph-walker-model-cache`: field classification; stripped SimpleModel roots; bounded double-checked class cache.
- **Provenance writes** — `provenance-folded-writes`: atomic fold (non-hybrid) / second-pass attach (hybrid); ledger precedes writes.
- **Triplet ranking** — `triplet-ranking-penalty-semantics`: penalty-default distances; raw-vs-blended eligibility guards; heapq.nsmallest.
- **Hybrid chunks** — `hybrid-rrf-chunk-summary-fusion`: RRF k∈[30,60]; multiplicative importance/truth/personal; empty-map = baseline.
- **Hybrid entities/facts** — `hybrid-entity-fact-lanes`: partition neighborhood triples; is-a pinned first; unscoped-empty budget hand-off.
- **Hybrid gating** — `hybrid-deferral-ladder`: raise on graph-only knobs; defer on custom type/neighborhood/feedback; collection check fails open.
- **Contradictions** — `contradiction-detection-additive-edges`: touched 1-hop region; rendered-fact anchoring; confidence threshold; swallow errors.
- **Supersession** — `functional-supersession-recency`: declared functional set; tag superseded/superseded_by; update-in-place via merge-on-identity.
- **Rendering** — `edge-to-text-rendering`: compact label in brackets; description suffix; __node_content_*__ fences.
- **Search facade** — `search-fanout-facade`: authorized fan-out; CODE seed-miss softening; back-compat projection layer.
- **Associations** — `chunk-associations-propose-verify`: limit=1 id resolution; sorted-pair dedup; LLM failure degrades, persistence raises.
- **Dry run** — `dry-run-cost-estimator`: estimate shares the routing module; no side effects; remote mode rejects.
- **Session turns** — `session-turn-arbitration`: gate before retrieval; effective_query threading; evidence only on string completions.
- **Qualification** — `pipeline-qualification-gate`: opt-in cache check; lock owns exclusion; stale STARTED must be clearable.
- **Vector fan** — `vector-search-fan-shapes`: shape-stable empties; lazy engine resolve; batch never ID-filtered.
- **DLT route** — `dlt-deterministic-route`: purge stale artifacts on stable ids; schema-derived edges; ctx.extras dedup state.
- **Code routes** — `code-route-dual-granularity`: sync factories; repo-level cross-file pass over per-file identity.
- **Global context** — `global-context-index-buckets`: memify bucket placement; prelude-first concatenation; opt-in top_k.
- **Weights** — `feedback-importance-weights`: project only when influence > 0; neutral 0.5 is exact no-op; separable channels.
- **RDF** — `rdf-export-uri-preservation`: ontology_valid/ontology_uri stamped at construction survive storage to export.
- **Unified engine** — `unified-engine-capabilities`: HYBRID_WRITE picks atomic dual-write vs split-parallel with deep copies.
- **Session distillation** — `session-distillation-graph`: distilled sessions reuse standard cognify tasks; batch skips session path.
- **Deletion** — `dataset-deletion-slug-protection`: slug-anchor survival rule; legacy-ledger routing; symmetric locking.
- **Result fusion** — `merge-results-conversational-reserve`: identity dedup before cap; reserved secondary slice.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
cognee (Apache-2.0), `main@a8f9760b` (v1.5.2); Codebase Memory project `ext-cognee` (27,603n / 163,303e, ready; head==base at pass-1 pin `a8f9760b`; parse_partial limited to frontend/deploy/test-fixture files — none cited).

## Full view (memory graph)
Revalidate `ext-cognee` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/cognee`, branch main @ `a8f9760bb6da90a9956b3be77c0d0534134f533a`. Direct-test suites live under `cognee/tests/unit/**` (409 test files) and run via `uv run --frozen pytest <paths>` (Python 3.11 host venv OK; some suites need LLM_API_KEY). Source and direct tests decide shipped claims.

## Boundaries
Adopt the engine contracts (route resolver, task dispatch, run lifecycle/rollback, deterministic identity, chunk reconstruction, triplet scoring, hybrid lane fusion, capability-gated writes). Adapt backend adapters (Ladybug/Neo4j/Kuzu/LanceDB/pgvector/Turso are host surface), prompt templates, and telemetry to your stack. Omit cognee's product transport — FastAPI routers (`cognee/api/v1/*`), MCP server (`cognee-mcp/`), Next.js UI (`cognee-frontend/`), distributed/deploy packaging, eval_framework, and Slack/cloud integrations — none affect pipeline correctness.
