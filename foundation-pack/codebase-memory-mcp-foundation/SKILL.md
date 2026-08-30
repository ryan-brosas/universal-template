---
name: codebase-memory-mcp-foundation
description: "Use when porting codebase-memory-mcp's C internals: SQLite graph store pragmas/integrity/quarantine, atomic publish pipeline, incremental closure routing, MCP server surface (TOON, profiles, cancellation), daemon rendezvous/version-cohort IPC, watcher/supervisor resilience, or the foundation allocator/lock/log primitives."
disable-model-invocation: true
---

# codebase-memory-mcp: code-graph engine — store, pipeline, MCP, and daemon kernel

## Use this for
Building or porting any local-first code-intelligence engine that turns a repo into a queryable symbol/edge graph served to AI agents: SQLite-backed graph storage with WAL discipline and integrity quarantine, staging→seal→atomic-rename publication with ADR capture, closure-budgeted incremental replanning, an MCP tool surface with token-frugal TOON emission and read-only profiles, an account-wide daemon with exact-build version cohorts and frozen wire envelopes, crash-containing index supervisors, adaptive watchers, and the C foundation primitives (arenas, interning, lock registries, subprocess classification) underneath. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump

Store & SQLite core
- `references/query-open-immutable-fallback.md` — why must read queries never mutate the DB file?
- `references/wal-pragma-ladder.md` — sharing a graph DB across processes without SIGBUS or starved WAL.
- `references/integrity-verdict-three-way.md` — HEALTHY/CORRUPT/UNOPENABLE verdict classes pinned per test.
- `references/seal-for-atomic-publish.md` — making a staging DB self-contained before atomic rename.
- `references/generation-cursor-staleness.md` — pagination tokens detecting graph changes underneath.
- `references/integrity-verdict-quarantine.md` — corrupt vs lost-lock-race verdicts.
- `references/store-resolve-ladder.md` — project name → store handle without ghosts or stale verdicts.
- `references/rowscan-error-discipline.md` — SCANCHK: terminal step rc must equal SQLITE_DONE.
- `references/cached-statement-release.md` — reset-before-park rule un-deadlocking WAL↔DELETE switches.
- `references/passive-checkpoint-policy.md` — checkpoint WITHOUT truncating live-reader WALs.
- `references/bulk-write-wal-invariants.md` — relax synchronous, never journal_mode.
- `references/page-cache-slab.md` — contiguous slab fixing per-request page-cache pinning.
- `references/store-transaction-trio.md` — BEGIN IMMEDIATE commit/rollback contract.
- `references/store-idle-release.md` — TTL store release + pristine-memory fast valve.
- `references/store-swap-visibility.md` — cached handles detecting atomic DB replacement.
- `references/store-restore-copy.md` — rowid-preserving store-to-store copy.
- `references/bfs-shortest-path-cte.md` — recursive CTE traversal with self-loop guards.
- `references/edge-props-commutative-merge.md` — deterministic parallel edge-property merging.
- `references/ac-lz4-batch-scan.md` — Aho-Corasick over LZ4 buffers with thread-local reuse.
- `references/architecture-orientation-endpoint.md` — bounded whole-repo orientation summaries.
- `references/cypher-parse-boundary.md` — typed AST + parameterized codegen parse boundary.
- `references/cypher-execution-deadline.md` — budgeted execution with hot-loop deadline checks.
- `references/cypher-crossjoin-guards.md` — plan-time cartesian-product refusal.
- `references/ignore-precedence-negation.md` — signed match-result ignore ladder with safety core.
- `references/project-name-derivation.md` — path→project-name safe-set mapping with hash suffix.

Nodes & queries
- `references/node-qn-identity.md` — (project, qualified_name) identity + FK cascade semantics.
- `references/batch-edge-upsert.md` — prepared batch inserts with UNIQUE coalescing.
- `references/qn-suffix-lookup.md` — dot-boundary suffix matching without false positives.
- `references/node-overlap-lookup.md` — line-range symbol lookup excluding containers.
- `references/batch-qn-resolution.md` — 500-QN resolution in one prepared pass, 0 = missing.
- `references/dependent-files-closure.md` — reverse deps minus self-reference and container noise.
- `references/file-hash-detection.md` — sha256-authoritative change detection with metadata fast-paths.
- `references/project-upsert-generation.md` — reindex idempotence driving mutation counters.
- `references/url-path-edge-lookup.md` — JSON-property edge queries and when they're acceptable.
- `references/node-degree-semantics.md` — single-edge-count degree API.
- `references/multitype-bfs.md` — direction+type-array traversal with budgets and edge provenance.
- `references/pagination-total-order.md` — unique tiebreaker before LIMIT/OFFSET.
- `references/degree-filter-sql.md` — derived-table fan-in/out filters + conditional count stripping.
- `references/entry-point-exclusion.md` — double-negation keeping dead code visible.
- `references/like-hint-prefilter.md` — advisory LIKE hints under decisive regex predicates.
- `references/search-label-filters.md` — parameterized NOT IN exclusion + runtime schema introspection.
- `references/file-pattern-substring.md` — documented substring file filters (#200).
- `references/empty-filter-omission.md` — omit-empty-arm dynamic WHERE construction.
- `references/case-folding-boundary.md` — flag-gated folding, hard exact-identity exceptions.
- `references/traverse-then-slice.md` — compute-once paginated traversals.
- `references/vector-search-int8-udf.md` — in-SQL cosine over int8 blobs + min-across-keywords rerank.
- `references/camel-split-fts.md` — dual-form FTS cells for identifier search.
- `references/fts-rebuild-fallback.md` — graceful UDF-dependent index rebuilds.
- `references/vocabulary-drift-guards.md` — bidirectional C-predicate ↔ SQL-literal consistency tests.
- `references/schema-as-data.md` — self-describing label/edge catalogs.
- `references/architecture-aspects-rollup.md` — aspect-parameterized boundaries/hotspots/clusters.
- `references/louvain-clustering.md` — pure-C Louvain/Leiden community detection.
- `references/scc-cycle-aspect.md` — size>1 SCC cycle reporting.
- `references/search-code-literal-floor.md` — guaranteed literal line scanner under fancy retrieval.
- `references/project-listing-shadows.md` — shadow-row conventions across all consumers.
- `references/index-status-dual-state.md` — stored vs live git state reporting.
- `references/dump-project-filter.md` — id-coherent filtered SQL dumps.
- `references/dump-verify-floors.md` — tiered count verification on import.
- `references/artifact-roundtrip.md` — zstd+manifest export with size/version gates.
- `references/coverage-honesty-contract.md` — skipped/parse_partial taxonomy + generation gates.
- `references/coverage-replace-transaction.md` — atomic coverage rewrites with timing ledgers.
- `references/parse-partial-capture.md` — range-precise parse telemetry with recovery awareness.
- `references/adr-section-merge.md` — closed-vocabulary section merge with pre-store size gate.
- `references/adr-capture-before-rebuild.md` — capture-with-abort preserving user content.
- `references/dbt-lineage-extraction.md` — last-string-arg relation extraction from templated SQL.
- `references/k8s-manifest-extraction.md` — key-allowlisted infra manifest mapping.
- `references/env-url-scanner.md` — exclusion-parity config walkers with secret filtering.
- `references/config-link-strategies.md` — graded config↔code linking with negative guards.
- `references/tests-edge-derivation.md` — convention-driven TESTS/TESTS_FILE edges.
- `references/decorator-route-plane.md` — four-phase idempotent Route/HANDLES materialization.
- `references/route-canon-cross-framework.md` — client↔handler route identity across frameworks.
- `references/service-pattern-classification.md` — callee QN → HTTP_CALLS/ASYNC/ROUTE_REG/CONFIGURES.
- `references/registry-resolution-ladder.md` — bare-name resolution with defensible confidence.
- `references/path-alias-scoped-resolution.md` — pluggable longest-prefix alias scopes.
- `references/minhash-lsh-clones.md` — banded LSH MinHash with content-derived pair ownership.
- `references/change-coupling-mining.md` — filter-then-count git history coupling edges.
- `references/transitive-loop-depth.md` — memoized cycle-safe metric propagation.
- `references/semantic-eleven-signal-blend.md` — zero-model SEMANTICALLY_RELATED scoring.
- `references/language-disambiguation.md` — ordered resolution ending in deterministic defaults.
- `references/glr-depth-cap.md` — merge-depth caps for ambiguous GLR parses.
- `references/lsp-surface-codec.md` — body-vs-signature edit encoding for dependents.
- `references/closure-repair-routing.md` — NOOP/CLOSURE_REPAIR/FORCED_FULL decision ladder.
- `references/incremental-route-observability.md` — compile-time seam atoms for route assertions.
- `references/incremental-accuracy-parity.md` — bounded per-type partial≈full parity proofs.
- `references/worker-pool-deep-stacks.md` — explicit-stack pthreads for recursive parsers.
- `references/parallel-parity-harness.md` — per-edge-type dual-engine equality.
- `references/env-access-convergence-probe.md` — named known-gap test design.
- `references/mkstemp-staging-security.md` — unpredictable exclusive staging creation.
- `references/publish-destination-races.md` — destination-existence deltas + sidecar vetoes.
- `references/quarantine-naming-protocol.md` — noreplace candidate scans with rollback.
- `references/quarantine-snapshot-discipline.md` — snapshot-verify-delete for DB+WAL pairs.
- `references/invalid-name-litter-guard.md` — validate-before-open against CWD pollution.
- `references/language-contract-suite.md` — full-pipeline invariant testing across languages.
- `references/scale-tier-contracts.md` — opt-in binary-level scale legs.
- `references/scale-fit-regression-gate.md` — pure log-ratio exponent fits vs synthetic pins.
- `references/subprocess-outcome-classification.md` — six-way child-death taxonomy + quiet-timeout hangs.
- `references/crash-containment-fixture.md` — poison-file fork-isolated containment proofs.
- `references/crash-durable-worker-log.md` — unbuffered+flush-per-line post-mortem guarantees.
- `references/index-supervisor-worker.md` — respawn supervision containing pathological files.
- `references/watcher-adaptive-polling.md` — size-scaled intervals + dual-signal prune gates.
- `references/watcher-git-probe-budgets.md` — deadline+output caps against hostile fsmonitor hooks.
- `references/watcher-baseline-discipline.md` — success-committed change baselines.
- `references/git-canonical-root.md` — resolve-then-realpath repo identity from subdirs/worktrees.
- `references/userconfig-extension-mapping.md` — two-tier merge with digests for new extensions.
- `references/auto-index-gating.md` — four-gate implicit background work ladder.
- `references/session-root-detection.md` — latched single-shot context detection.
- `references/allocator-binding-order.md` — bind-first allocator routing with asserts.
- `references/memory-budget-resolver.md` — pure RAM-fraction budget resolution with strict overrides.
- `references/memory-phase-accounting.md` — gapless phase marks + post-release censuses.
- `references/arena-intern-discipline.md` — same-lifetime arenas + pointer-identity interning.
- `references/arena-eager-commit-gating.md` — OS-cost-conditioned allocator options.
- `references/arena-census-diagnostics.md` — legend-driven retention vs shape diagnosis.
- `references/private-lock-fd-discipline.md` — consume-on-invoke close semantics.
- `references/lock-registry-turn-rw.md` — writer-preference rw locks from plain files.
- `references/lock-cancel-no-barge.md` — sticky cancel tokens without barging.
- `references/lock-registry-retirement.md` — generation-token ABA defense on free.
- `references/yaml-subset-parser.md` — documented-subset parsing with refusal lists.
- `references/sanitizer-aware-budgets.md` — one-predicate instrumented detection.
- `references/shell-arg-validation.md` — deny-list + double-quote template pairing.
- `references/sqlite-authorizer-defense.md` — authorizer-level ATTACH denies.
- `references/vendored-integrity-manifest.md` — fail-closed checksum manifests.
- `references/diagnostics-output-safety.md` — fail-closed temp diagnostics files.

MCP server surface
- `references/toon-token-frugal-emission.md` — header-once tabular output with field blocklists.
- `references/toon-quoting-grammar.md` — exact cell-quoting predicate.
- `references/format-duality-contract.md` — one model, two serializations.
- `references/cell-utf8-sanitization.md` — per-cell UTF-8 guarantees for line tools.
- `references/snippet-context-bomb-guard.md` — 500-line clip + source_clipped flags.
- `references/snippet-resolution-ladder.md` — disclosed-tier name resolution.
- `references/source-lossy-utf8.md` — lossy-with-structure source sanitization.
- `references/tools-list-pagination.md` — lazy cursor-in/pages-out catalogs.
- `references/tool-profile-allowlist.md` — static analysis/scout tiers, fail-closed parsing.
- `references/tool-annotations-contract.md` — four-axis safety metadata (honest destructive-query entries).
- `references/cancellation-scoping.md` — dual-form id matching + depth-scoped flag resets.
- `references/string-id-passthrough.md` — opaque JSON-RPC id echo (#253).
- `references/envelope-duplication-gate.md` — whole-catalog no-duplication property tests.
- `references/lean-defaults-contract.md` — advertise-only-emittable coherence.
- `references/numeric-arg-honesty.md` — schema-runtime bound agreement (#1511).
- `references/tail-resolution-convenience.md` — unique-tail project resolution with ambiguity refusal.
- `references/postfilter-total-consistency.md` — totals computed after filtering.
- `references/minhop-trace-union.md` — multi-seed BFS with min-hop aggregation.
- `references/strategy-class-closure.md` — closed edge-strategy trust vocabularies.
- `references/depth-clamp-policy.md` — clamp-don't-reject depth arguments.
- `references/hunk-scoped-impact-seeds.md` — diff-overlap blast-radius seeding.
- `references/impact-summary-hops.md` — hop-bucketed impact with pure risk mapping.
- `references/trace-ingest-helpers.md` — pure OTLP extraction helpers.
- `references/workflow-prompts-surface.md` — drift-guarded multi-tool recipes.
- `references/hook-augment-never-deny.md` — fail-open exit-0 hook contracts.
- `references/hook-conflict-ownership.md` — script-identity hook ownership rules.
- `references/ui-rpc-readonly-gate.md` — reject-duplicate headers + positive read allowlists.
- `references/agent-client-profiles.md` — declarative capability-bitmask agent registry.
- `references/agent-profile-renderers.md` — expectation-table dialect emitters.
- `references/progress-sink-rendering.md` — gated structured-log progress rendering.
- `references/config-safe-editing.md` — identity-CAS config upserts, fail-closed links.
- `references/activation-transaction-staging.md` — stage/validate/finalize binary replacement.
- `references/activation-guard-diagnostics.md` — BUSY-vs-refused remediation-specific messages.
- `references/bootstrap-role-routing.md` — single-classifier argv role routing.
- `references/bootstrap-launch-spec.md` — detached non-inheriting daemon spawn specs.
- `references/cross-repo-bidirectional-edges.md` — caller↔handler edges across two DBs without half-links.
- `references/multi-project-guard-ordering.md` — sorted multi-project lease acquisition with cancel checks.
- `references/index-root-safety.md` — overbroad-root refusal + allowed-root gates.
- `references/eviction-case-matrix.md` — four-case store cache eviction pins.

Daemon & coordination
- `references/project-lock-two-key.md` — SH-set + EX-member per-project serialization.
- `references/version-cohort-exact-build.md` — byte-fingerprint admission cohorts.
- `references/build-fingerprint-capture.md` — capture-once executable hashing.
- `references/rendezvous-key-stability.md` — product-domain endpoint naming inversion.
- `references/cohort-cache-fingerprint-split.md` — wire vs data-domain identity layering.
- `references/cohort-startup-lifetime-split.md` — purpose-per-lock-file discipline.
- `references/cohort-mutation-barrier.md` — intent→admission→probe quiesce barriers.
- `references/conflict-record-population.md` — populate-first per-cause conflict records.
- `references/conflict-log-rotation.md` — durable private rotating conflict journals.
- `references/daemon-job-serialization.md` — scoped job FSMs with admission staleness checks.
- `references/daemon-application-job-fsm.md` — subscribe/own/terminal job lifecycle.
- `references/daemon-ipc-endpoint-security.md` — OS-scoped endpoints + anchor/temp-link publication.
- `references/windows-nonce-record.md` — canonical nonce artifacts where sockets can't hold identity.
- `references/ipc-probe-fail-closed.md` — refused-means-active liveness probes.
- `references/ipc-framing-discipline.md` — validate-then-allocate length-prefix framing.
- `references/frame-op-codes.md` — exact-layout op framing with unidentified-connection caps.
- `references/frozen-rendezvous-wire.md` — generation-zero stable envelopes + out-of-band ABIs.
- `references/hello-exchange-encode.md` — fixed-frame strict handshake encoders.
- `references/activation-shutdown-protocol.md` — cross-version escape protocols sharing the frozen header.
- `references/runtime-client-wait-semantics.md` — WAIT_FOREVER sentinels with interrupt handles.
- `references/runtime-client-leases.md` — lease-bundled spawn-free runtime layering.
- `references/connect-result-layering.md` — transport×policy×payload result structs.
- `references/daemon-stop-drain.md` — peer-verified control frames, self-excluding snapshots.
- `references/daemon-http-host-reconciliation.md` — reconciled adoption + refusal-as-result hosts.
- `references/host-reconcile-test-seams.md` — decision-injection lifecycle testing.
- `references/host-lifecycle-states.md` — prepare/reconcile/refuse/terminate state machines.
- `references/daemon-frontend-stdio-bridge.md` — strict-shape notifications + lossless backpressure.
- `references/stdio-buffering-hang.md` — FILE*-vs-poll drain-or-block bug class.
- `references/overflow-fixture-design.md` — precondition-satisfying bounds-test fixtures.

## Capsule map
- **Store open & integrity** — `query-open-immutable-fallback`: query-only opens never mutate; `wal-pragma-ladder`: busy_timeout/WAL/synchronous ladder with SIGBUS guard; `integrity-verdict-quarantine` + `integrity-verdict-three-way`: HEALTHY/CORRUPT/TRANSIENT verdict taxonomy pinned per class; `store-resolve-ladder`: cache → guarded-verdict → internal-name scan; `rowscan-error-discipline`: terminal DONE checks; `cached-statement-release`: reset-before-park; `passive-checkpoint-policy`: mode-appropriate WAL checkpoints; `bulk-write-wal-invariants`: relax synchronous, never journal_mode; `store-transaction-trio`: BEGIN IMMEDIATE contract; `store-idle-release`: TTL release + pristine valve; `store-swap-visibility`: handle-staleness detection; `eviction-case-matrix`: four eviction pins.
- **Nodes & queries** — `node-qn-identity`: (project, qn) upsert identity + cascade; `batch-edge-upsert`: prepared UNIQUE-coalescing batches; `qn-suffix-lookup` + `batch-qn-resolution` + `node-overlap-lookup`: lookup primitives; `multitype-bfs` + `bfs-shortest-path-cte`: traversals with provenance and loop guards; `pagination-total-order` + `degree-filter-sql` + `entry-point-exclusion` + `like-hint-prefilter` + `search-label-filters` + `file-pattern-substring` + `empty-filter-omission` + `case-folding-boundary` + `traverse-then-slice` + `vector-search-int8-udf` + `camel-split-fts` + `fts-rebuild-fallback`: search machinery; `vocabulary-drift-guards`: C↔SQL vocabulary consistency tests; `schema-as-data` + `architecture-aspects-rollup` + `architecture-orientation-endpoint` + `louvain-clustering` + `scc-cycle-aspect` + `search-code-literal-floor` + `project-listing-shadows` + `index-status-dual-state` + `dump-project-filter` + `store-restore-copy` + `url-path-edge-lookup` + `node-degree-semantics` + `generation-cursor-staleness`: introspection surfaces.
- **Publish pipeline** — `mkstemp-staging-security`: unpredictable exclusive staging; `seal-for-atomic-publish`: WAL removal + DELETE mode + TRUNCATE checkpoint; `publish-destination-races`: existence-delta abort + sidecar veto; `quarantine-naming-protocol`: `.corrupt.N` candidate scan with rollback; `quarantine-snapshot-discipline`: snapshot-verify-delete db+wal; `adr-capture-before-rebuild`: NOT_FOUND-vs-error separation; `adr-section-merge`: closed-vocabulary section merge; `artifact-roundtrip`: manifest-gated zstd exchange; `dump-verify-floors`: floor/ratio verification.
- **Incremental & passes** — `closure-repair-routing`: NOOP/repair/full ladder with budget fallbacks; `incremental-route-observability`: compile-time seam atoms; `incremental-accuracy-parity`: ±2 per-type parity; `file-hash-detection`: hash-authoritative change; `dependent-files-closure`: filtered reverse deps; `lsp-surface-codec`: body/signature edit encoding; `watcher-baseline-discipline`: success-committed baselines; `cross-repo-bidirectional-edges` + `edge-props-commutative-merge` + `ac-lz4-batch-scan` + `cypher-parse-boundary` + `cypher-execution-deadline` + `cypher-crossjoin-guards` + `ignore-precedence-negation` + `project-name-derivation` + `invalid-name-litter-guard` + `multi-project-guard-ordering` + `index-root-safety` + `source-lossy-utf8`: pass-level contracts.
- **MCP surface** — `toon-token-frugal-emission` + `toon-quoting-grammar` + `format-duality-contract`: token-frugal dual-format emission; `cell-utf8-sanitization`: per-cell UTF-8; `snippet-context-bomb-guard` + `snippet-resolution-ladder`: capped disclosed-tier snippets; `tools-list-pagination` + `tool-profile-allowlist` + `tool-annotations-contract`: catalog shape; `cancellation-scoping` + `string-id-passthrough`: request correlation; `envelope-duplication-gate` + `lean-defaults-contract` + `numeric-arg-honesty` + `postfilter-total-consistency`: response honesty properties; `tail-resolution-convenience` + `minhop-trace-union` + `strategy-class-closure` + `depth-clamp-policy` + `hunk-scoped-impact-seeds` + `impact-summary-hops` + `trace-ingest-helpers` + `workflow-prompts-surface`: tool behaviors.
- **Agent integration** — `hook-augment-never-deny` + `hook-conflict-ownership`: hooks that can never block; `ui-rpc-readonly-gate`: browser-safe RPC; `agent-client-profiles` + `agent-profile-renderers`: table-driven onboarding; `progress-sink-rendering`: gated progress; `config-safe-editing` + `activation-transaction-staging` + `activation-guard-diagnostics`: safe self-installation; `bootstrap-role-routing` + `bootstrap-launch-spec`: role dispatch.
- **Daemon coordination** — `project-lock-two-key` + `version-cohort-exact-build` + `build-fingerprint-capture`: identity and locking primitives; `rendezvous-key-stability` + `cohort-cache-fingerprint-split` + `cohort-startup-lifetime-split` + `cohort-mutation-barrier`: cohort protocol layers; `conflict-record-population` + `conflict-log-rotation`: diagnosable conflicts; `daemon-job-serialization` + `daemon-application-job-fsm`: job FSMs; `daemon-ipc-endpoint-security` + `windows-nonce-record` + `ipc-probe-fail-closed` + `ipc-framing-discipline` + `frame-op-codes`: transport security; `frozen-rendezvous-wire` + `hello-exchange-encode` + `activation-shutdown-protocol` + `runtime-client-wait-semantics` + `runtime-client-leases` + `connect-result-layering`: wire protocol; `daemon-stop-drain` + `daemon-http-host-reconciliation` + `host-reconcile-test-seams` + `host-lifecycle-states` + `daemon-frontend-stdio-bridge` + `stdio-buffering-hang` + `overflow-fixture-design`: host lifecycle and its testing.
- **Extraction passes** — `route-canon-cross-framework` + `decorator-route-plane` + `service-pattern-classification` + `tests-edge-derivation` + `config-link-strategies` + `dbt-lineage-extraction` + `k8s-manifest-extraction` + `env-url-scanner`: edge planes; `registry-resolution-ladder` + `path-alias-scoped-resolution`: name binding; `minhash-lsh-clones` + `change-coupling-mining` + `transitive-loop-depth` + `semantic-eleven-signal-blend`: derived intelligence; `language-disambiguation` + `glr-depth-cap`: language handling; `parse-partial-capture` + `coverage-honesty-contract` + `coverage-replace-transaction`: coverage honesty; `worker-pool-deep-stacks` + `parallel-parity-harness` + `env-access-convergence-probe` + `language-contract-suite` + `scale-tier-contracts` + `scale-fit-regression-gate` + `crash-containment-fixture`: execution and verification strategy.
- **Foundation primitives** — `allocator-binding-order` + `memory-budget-resolver` + `memory-phase-accounting` + `arena-intern-discipline` + `arena-eager-commit-gating` + `arena-census-diagnostics` + `page-cache-slab`: memory; `private-lock-fd-discipline` + `lock-registry-turn-rw` + `lock-cancel-no-barge` + `lock-registry-retirement` + `project-lock-two-key`: locking; `subprocess-outcome-classification` + `crash-durable-worker-log` + `diagnostics-output-safety` + `index-supervisor-worker` + `watcher-adaptive-polling` + `watcher-git-probe-budgets`: process supervision; `yaml-subset-parser` + `sanitizer-aware-budgets` + `shell-arg-validation` + `sqlite-authorizer-defense` + `vendored-integrity-manifest` + `git-canonical-root` + `userconfig-extension-mapping` + `auto-index-gating` + `session-root-detection` + `project-name-derivation` + `project-upsert-generation`: platform glue.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Rich remaining seams for future passes: `src/cli/cli.c` install/uninstall flows beyond activation (12.8k lines), `src/ui/httpd.c` parser internals, `internal/cbm/sqlite_writer.c` dump formats, `src/pipeline/pass_lsp_cross.c` language-server plumbing, `src/cypher/cypher.c` full grammar surface, Windows-specific paths in `src/foundation/platform.c`.

## Provenance
codebase-memory-mcp (MIT), `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5` (live HEAD verified 2026-08-24); Codebase Memory project `ext-codebase-memory-mcp` (root `/mnt/hdd/utopia/inspo/external/codebase-memory-mcp`, branch main, ready FULL, 23,739n/134,638e, head==base 010569fa). Coverage caveat: parse_partial spans exist in ~68 files (mostly string-heavy C regions tree-sitter recovers around); none of the ranges cited by these capsules fall inside flagged spans — verify with `check_index_coverage` if porting from flagged files (`src/cli/cli.c`, `src/daemon/ipc.c`, `src/foundation/private_file_lock.c` carry wide spans).

## Full view (memory graph)
Revalidate `ext-codebase-memory-mcp` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Direct suite executed at this pin via `make -f Makefile.cbm build/c/test-runner SANITIZE= GCC_ONLY_FLAGS="-Wno-error=free-nonheap-object ..."` then `./build/c/test-runner <suites>`: ~3,040 passing across 36 suites (18 skips; env-sensitive failures recorded honestly in the work record: cli ×10 hook-integration, limits ×1, mem_profile ×1).

## Boundaries
Adopt the pure contracts: WAL/journal discipline, seal-then-rename publication, generation cursors, SCANCHK/reset-before-park statement rules, TOON quoting/blocklists, closed strategy vocabularies, frozen wire envelopes, cohort admission, quiet-timeout hang classification, fail-open hooks, hash-authoritative change detection. Adapt SQLite spellings, pragma values, thresholds (LSH bands, coupling floors, poll intervals), file layouts, and vendor payloads to your host. Omit codebase-memory-mcp-specific surfaces: the embedded 3D graph UI bundle, the specific MCP tool catalog names, per-agent installer tables you don't target, and the vendored tree-sitter grammars.
