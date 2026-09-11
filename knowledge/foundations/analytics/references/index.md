<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Plausible Analytics: ClickHouse web-analytics foundation

## Use this for
Use when building or fixing a web-analytics/OLAP reporting layer: splitting mixed metrics across event/session tables, compiling filter grammars to SQL, generating dense time-bucket axes, comparing periods, ingesting high-volume events through batched buffers with in-memory session tracking, or measuring engaged time client-side. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./query-runner-comparison-shapes.md` — run pipeline; two comparison result shapes; goal-index decode.
- `./optimizer-step-pipeline.md` — ordered business-rule rewrites; time-granularity resolution; split-with-renames.
- `./table-decider-partitioning.md` — three-input partition closure deciding one-table vs join; smearing gate.
- `./sql-builder-subquery-joins.md` — subquery recombination, windowed total_rows, dimension provenance side.
- `./session-metric-sign-arithmetic.md` — CollapsingMergeTree-safe ratio metrics with underflow clamps.
- `./timeslots-session-smearing.md` — clamped timeSlots expansion; 15-min sub-slots for fractional-hour zones.
- `./goal-array-index-join.md` — single-scan arrayIntersect goal matching over parallel arrays.
- `./where-builder-filter-grammar.md` — recursive filter compiler; table-scoped no-ops; has_done subqueries; PK lower bound.
- `./session-cache-store.md` — 30-min latch, sign-pair updates, phash2-sharded balancer serialization.
- `./write-buffer-rowbinary.md` — byte-counted batching with compile-time-frozen INSERT statements.
- `./ingestion-event-pipeline.md` — ordered drop-gates before enrichment; 200ms UA timeout; salted SipHash identity.
- `./persistor-backend-rollout.md` — percent-gated backend selection keyed on user_id.
- `./cache-adapter-warmer.md` — exit-catching partitioned ConCache adapter; all/updated-recently refresh pair.
- `./time-labels-comparison-ranges.md` — label-axis generation; contiguous previous-period shifts; leap-year YoY.
- `./imported-merge-plane.md` — dimension→import-table routing; lossy top-N×100 join; weighted metric recombination.
- `./sampling-budget-ladder.md` — 10M-event scan budget → SAMPLE fraction with honesty multipliers (EE).
- `./session-transfer-tinysock.md` — version-fingerprinted session-cache handoff over Unix sockets between deploys.
- `./tracker-engagement-protocol.md` — visibility-banked engaged time; monotonic scroll-depth send gate.

## Capsule map
- **Query execution** — `query-runner-comparison-shapes`: optimize→run→compare pipeline; timeseries keeps two lists joined by label-zip, dimensional merges inline; goals decode by 1-based index into preloaded list.
- **Query execution** — `optimizer-step-pipeline`: fixed-order reduce of 9 rewrite steps; granularity ladder ≤48h→hour, ≤40d→day, ≤52w→week else month; sessions sub-query renames event:page→visit:entry_page.
- **Query planning** — `table-decider-partitioning`: metrics×dimensions×filter-dimensions partition into event/session/either buckets; visitors+visits become smeared sessions queries on minute/hour without goal filters.
- **Query planning** — `sql-builder-subquery-joins`: first table is outer FROM, later tables join as subqueries on ALL dimension equality; pagination + `count() over ()` apply to the JOINED result only.
- **Metrics math** — `session-metric-sign-arithmetic`: ratios divide by `sum(sign)` not row count; `greatest(ifNotFinite(x,0),0)` double clamp prevents UInt underflow >100% bounce rates.
- **Metrics math** — `timeslots-session-smearing`: ARRAY-JOIN over `timeSlots(clamped start, clamped duration, step)`; hour granularity uses 900s slots then toStartOfHour for GMT±X:45 zones.
- **Dimension compilation** — `goal-array-index-join`: multiMatchAllIndices(page regexes) ∩ predicate-filtered indices returns goal-position arrays used as GROUP BY keys; no-props variant skips Array(String) meta columns.
- **Dimension compilation** — `where-builder-filter-grammar`: nested [op, dim, clauses] AST compiles recursively; wrong-table dimensions compile to literal true; garbage filter ⇒ false (fail closed); sessions range keeps a redundant `start >= first−7d` for sample-factor honesty.
- **Session state** — `session-cache-store`: per-user phash2 worker GenServers serialize read-modify-write; 30-minute latch; engagement only refreshes timestamp; updates buffer [sign:-1 old, sign:+1 new].
- **Ingestion** — `write-buffer-rowbinary`: cast bytes into an iodata buffer sized by IO.iodata_length; INSERT SQL + header frozen at compile time; flush on size/tick/call/terminate; trap_exit swallows linked-process deaths.
- **Ingestion** — `ingestion-event-pipeline`: ~17-step reduce_while with halt-on-drop ordered cheap-checks-first; UA parse via cached nolink task killed at 200ms; user_id = SipHash(salt, ua+ip+domain+root_domain) with current+previous salt window.
- **Ingestion** — `persistor-backend-rollout`: `phash2(user_id,100)+1 <= percent_enabled` picks embedded vs remote backend so a visitor never straddles paths.
- **Caching substrate** — `cache-adapter-warmer`: every adapter op catches :exit → miss; partitions routed by phash2; warmer runs :all (delete-stale) and :updated_recently (15-min merge) cycles; disabled cache falls back to get_from_source.
- **Time semantics** — `time-labels-comparison-ranges`: labels are display-string join keys generated backwards for months; previous_period shift uses `diff − 1` for contiguity; match_day_of_week snaps via nearest-weekday-excluding-self.
- **Imported data** — `imported-merge-plane`: dims route to exactly ONE import table or imports skip with a surfaced reason; ratio metrics recombine through `__internal_*` denominator columns.
- **Sampling (EE)** — `sampling-budget-ladder`: fraction = 10M / estimated events, skipped under 1 day or above 0.4; every metric × `any(_sample_factor)` keeps numbers absolute.
- **Deployment** — `session-transfer-tinysock`: new node drains the old node's session cache over Unix sockets guarded by a 4-module MD5 fingerprint and `[:safe]` term decoding.
- **Client protocol** — `tracker-engagement-protocol`: engaged ms banked on blur/hidden, resumed when visible+focused; send gated on new max scroll depth OR ≥3000ms; SPA pageviews trigger prior page's engagement first.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question (candidates: imported-data merge plane `stats/imported/*`, SpecialMetrics composition `sql/special_metrics.ex`, CSV export streaming `dashboard/csv_export.ex`, legacy API surface `legacy/*`). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Plausible Analytics (AGPL-3.0 — license gates commercial porting), `master@9cc669b97ece3ecd37fcb3950791cb3873d7944d`; Codebase Memory project `ext-analytics` (ready FULL, 14,013n/51,049e, gen 2026-08-23T11:38:26Z, head==base_sha zero drift; parse_partial ×7 asset/fixture/SQL-dump files only, none cited).

## Full view (memory graph)
Revalidate `ext-analytics` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: partition closure, sign arithmetic, smearing expansion, index-encoded goal joins, byte-buffer batching, hash-percent rollout. Adapt host-specific integrations: Ecto/Ecto.Adapters.ClickHouse fragments, ConCache/:gen_cycle, Phoenix telemetry names, app-env thresholds. Omit product behavior: EE-only revenue/shields/replay planes (`on_ee` branches), billing/feature gating, Plausible dashboard frontend (`assets/js/dashboard/`), relay/remote persistence topology.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`cache-adapter-warmer.md`](./cache-adapter-warmer.md)
- [`goal-array-index-join.md`](./goal-array-index-join.md)
- [`imported-merge-plane.md`](./imported-merge-plane.md)
- [`ingestion-event-pipeline.md`](./ingestion-event-pipeline.md)
- [`optimizer-step-pipeline.md`](./optimizer-step-pipeline.md)
- [`persistor-backend-rollout.md`](./persistor-backend-rollout.md)
- [`query-runner-comparison-shapes.md`](./query-runner-comparison-shapes.md)
- [`sampling-budget-ladder.md`](./sampling-budget-ladder.md)
- [`session-cache-store.md`](./session-cache-store.md)
- [`session-metric-sign-arithmetic.md`](./session-metric-sign-arithmetic.md)
- [`session-transfer-tinysock.md`](./session-transfer-tinysock.md)
- [`sql-builder-subquery-joins.md`](./sql-builder-subquery-joins.md)
- [`table-decider-partitioning.md`](./table-decider-partitioning.md)
- [`time-labels-comparison-ranges.md`](./time-labels-comparison-ranges.md)
- [`timeslots-session-smearing.md`](./timeslots-session-smearing.md)
- [`tracker-engagement-protocol.md`](./tracker-engagement-protocol.md)
- [`where-builder-filter-grammar.md`](./where-builder-filter-grammar.md)
- [`write-buffer-rowbinary.md`](./write-buffer-rowbinary.md)
