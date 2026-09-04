<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Pi-Fovea: Foveated Repo-Mapping Extension (Heat-Diffusion Context Engine)

## Use this for
Build a repository-mapping context engine that gives an LLM a whole-repo map inside a hard token budget — sharp where it works, cheap everywhere else. The repo compiles once into a cross-language graph (symbols, files, route anchors); queries become interest vectors diffused as heat over the graph's Laplacian via a shared Chebyshev recurrence; rendering tiers the field into hot signatures, warm mentions, and collapsed glow within budget. Continuous turn-sync detects semantic drift after every assistant turn, attributes each change to the session that made it via content-hash transition journals (steer NOW for your own work, queue for next prompt when a sibling session moved the tree), and steers through a per-node charged heat memory that kills re-disclosure loops by construct. Nested repositories inside an umbrella workspace stay unindexed until work touches them. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. The repo ships a real vitest suite — 160/160 tests pass at HEAD (v0.18.3) — so every capsule's Probe is pinned to direct on-disk tests.

## Load the matching source dump
- `./heat-kernel-chebyshev.md` — evaluating e^{-tL} at many timescales from ONE walk: shared T_k vectors, Bessel coefficients, no-Jackson-window rationale.
- `./conductance-csr.md` — typed directed-ish edges → symmetric diffusion operator: max-conductance symmetrization, degree array, deg-0 guard.
- `./foveated-budget-renderer.md` — heat-tier rendering under hard token budgets: monotone-prefix binary search, delta disclosure, artifact⇔footer coupling.
- `./literal-join-index.md` — the cross-language bridge: placeholder normalization, per-(key,file) DF dedup, banded-IDF edge gating, clique decay.
- `./sync-surprise-gate.md` — steering verdicts: channel priors × per-node charged ledger × hysteresis, carrier-evidence gating for anchor deltas.
- `./cochange-history-overlay.md` — git co-edit affinity as recency-decayed seed overlay instead of permanent structure.
- `./route-anchor-pack.md` — five port shapes as data: rule pack, $P node capture, class prefixes, verb-in-path/ANY-mounts, file-convention routes, double-hash cache invalidation.
- `./discovered-route-rules.md` — statistical autonomy: Jeffreys-smoothed per-argument posteriors, cliff calibration, half-gravity probation.
- `./honest-fact-cache.md` — streaming JSONL content-hash cache: stat manifests, bounded prefetch, taint ledger drained exactly twice, atomic persists.
- `./file-source-overlay.md` — how do extraction stages reuse bytes the hash pass already read without pinning the whole repo in memory?
- `./import-resolution.md` — four language families resolved via suffix indexes with uniqueness gates; cardinality-decayed call edges; builtin wards.
- `./anchor-hub-collapse.md` — one feature hub per normalized route across server+client sites; sqrt-decayed site conductance.
- `./tui-safe-scheduling.md` — global spawn semaphore + order-preserving maps + in-sweep yields so heavy sweeps never freeze a live UI.
- `./basins-feature-regions.md` — conductance-cut feature regions for anchor-sparse repos (CLIs/libraries): triangle-density seeds, swallow guard.
- `./fuzzy-seed-resolution.md` — approximate queries: term-split/stem equivalence, route-prefix seeding, never-empty suggestion contract.
- `./warm-defer-sync-pipeline.md` — proactive context without blocking sends: edit-time warm keyed by drift identity, defer-or-render on Enter, turn_end backstop.
- `./hybrid-grep-router.md` — augment native search with graph navigation: query-shape classification, never-throw fallback ladder, labeled degradation.
- `./session-reload-state.md` — session-local disclosure vs process-global versioned ledgers on a Symbol.for slot; collectible vector-cache eviction.
- `./config-two-scope-model.md` — global defaults ← trusted project overrides ← env kill-switch; legacy-key migration; bounded knobs; atomic saves.
- `./state-lifecycle-checkout.md` — probe-as-oracle generations, reflog-qualified checkout quieting, stat-arbitrated resurrection, serialized fact passes.
- `./impact-cascade.md` — review-order prediction: single diffusion seeded with history partners, node-granular causal reasons, structured warmed* payload.
- `./four-ops-disclosure-loop.md` — sketch/focus/dwell/impact as one operator at four timescales over one disclosure ledger.
- `./mutation-provenance-journals.md` — crash-safe per-session tempdir journals of before/after content hashes: capture-before-write receipts, per-target write queues, read-your-writes drain, torn-journal recovery.
- `./sha-transition-ownership-lattice.md` — attribution as reachability: sha→sha edges accumulate owner sets; final-sha owners classify current/other/mixed/unattributed; deletions are first-class states.
- `./provenance-delivery-routing.md` — attribution gates the CHANNEL, not the alarm: only other-session drift defers to next-prompt; mixed/unattributed still steer immediately.
- `./progressive-nested-disclosure.md` — umbrella workspaces index nested repos only when work touches them: marker-chain enrollment on first hint or collapsed gitlink drift, vanish-triggered purge, header-persisted across restarts.
- `./outside-attention-rebaseline.md` — out-of-scope drift adopts silently: fresh baseline preserving heat/latch/embed-once, outsideAttention ack, no replay next turn.
- `./fact-pass-chain.md` — one never-rejecting process-wide chain serializing ALL extraction passes because the failure ledger would misblame overlapping ones.
- `./generated-source-skip.md` — minified-bundle DoS tripwire (4k-char line or .min/.bundle name): fact-free cached skip, honest report bucket, never tainted.
- `./agent-dir-shim.md` — duplicate the host's 10-line dir resolution in-process rather than pay its module-graph load; override env var must keep winning.

 - `./astgrep-rule-scan-runner.md` — external pattern-rule execution: all-or-nothing chunk trust, poison-line streaming parse, capability probes with sticky/TTL memoization.
- `./consolidated-fact-scan.md` — imports + calls + literals from ONE prefixed-rule pass; call wards compiled into rule constraints.
- `./literal-site-harvest.md` — where literal sites come from: code string patterns, template sweeps, and bare-scalar config joins under one shared path/env vocabulary.
- `./language-routing-tables.md` — extension-tier routing (full extraction vs outline-only vs config) and the undefined-fallback honesty contract for old extractor versions.
- `./git-porcelain-oracle.md` — fail-safe porcelain probe (`relist` on parse surprise), prefix-relative paths, reflog checkout classifier, PR diff seeding.
- `./graph-project-reregistration.md` — keeping Retrieve citations alive across graph re-registration: detection ladder + uniform repair protocol.

## Capsule map
- **Heat kernel** — `heat-kernel-chebyshev.md`: `chebyshevVectors`/`heatField` — walk once, recombine cached T_k(M)s per timescale; Jackson window deliberately omitted (smooth kernel, superalgebraic truncation decay).
- **CSR operator** — `conductance-csr.md`: `buildCsr` — unordered-pair MAX dedupe, both-direction CSR, degree = D^{-1/2} input; isolated nodes are fixed points, not NaNs.
- **Renderer** — `foveated-budget-renderer.md`: `revealFoveated` — hot/warm/glow tiers vs field max; byte-monotone prefix binary search can NEVER exceed budget; disclosed ids suppressed unless nucleus; overflow artifact always backs the footer's "full list" claim.
- **Literal joins** — `literal-join-index.md`: `buildJoinIndex` — rarity IS the ranking signal (edges only for df∈[2,48]); `:id`/`{id}`/`${id}` normalize to one `{*}` token.
- **Sync gate** — `sync-surprise-gate.md`: `sync()` — red only on evidential structural change or channel-adjusted per-node surprise above threshold minus the wall-clock-decayed ledger; ping-pong edits die by construct; coverage gaps are never deletions.
- **Co-change** — `cochange-history-overlay.md`: `coChangeHistory`/`historySeedWeights` — Jaccard-tilted pair scores cached raw, decayed at USE time, seeded into the SAME diffusion; history is not structure.
- **Anchor pack** — `route-anchor-pack.md`: `extractAnchors`/`loadRepoRules` — rules are data; the validated path string is the discriminator, the call shape is flavor; pack-hash invalidates caches on upgrade.
- **Discovery** — `discovered-route-rules.md`: `harvestFile`/`promote` — p̂=(pathN+.5)/(n+1) ≥ 0.55 with n≥4 sites in ≥2 files promotes implicit half-weight rules; junk band ≈0.27 vs real ≈0.75.
- **Fact cache** — `honest-fact-cache.md`: `loadFacts`/`refreshFacts` — failed ast-grep facts serve the session but persist ONLY hash markers; unchanged failures aren't retried; reports keep thin graphs honest.
- **File-source overlay** — `file-source-overlay.md`: pre-seeded path→text overlay from the bounded prefetch window + per-file single-flight reads; `readAll` returns only readable files, reads never throw.
- **Import/call resolution** — `import-resolution.md`: `resolveImportToFile` — family ladders (NodeNext .js→.ts strip, Go suffix match, Rust mod.rs, TS tail stem); ambiguous = unresolved; call conductance decays with definition cardinality (>48 candidates skipped).
- **Anchor hubs** — `anchor-hub-collapse.md` — one node per normalized route label; w=(implicit?0.5:1)/√sites; file hoods capped ≤12.
- **Scheduling** — `tui-safe-scheduling.md`: one global spawn semaphore (default 3), mapLimit preserves input order, forEachChunked yields per batch; adaptive chunk split on maxBuffer breach.
- **Basins** — `basins-feature-regions.md`: `detectBasins` — greedy ratio-growth until cut > 2.6× internal; symbol-only eligible seeds; >⅓-of-graph regions discarded.
- **Seed resolution** — `fuzzy-seed-resolution.md`: `resolveSeeds` — literal→name→substring→inflection→path-suffix ladder; misses render Dice-scored nearby symbols, never empty answers.
- **Warm/defer pipeline** — `warm-defer-sync-pipeline.md`: `warmSync` precomputes fingerprint+cascade on edit debounce; send path defers or renders prepared verdicts; warm == inline bit-for-bit.
- **Grep router** — `hybrid-grep-router.md`: symbol-like queries navigate the graph; options/regex stay native; graph errors degrade to native WITH a marker note; seedless appends nothing.
- **Session/reload state** — `session-reload-state.md`: disclosure dies with conversations; baselines survive in-process reloads behind a shape-version stamp.
- **Config scopes** — `config-two-scope-model.md`: defaults←global←project(trusted)←env; explicit keys beat legacy booleans; budgets clamped; tmp-rename saves.
- **State lifecycle** — `state-lifecycle-checkout.md`: inflight-deduped generations; reflog "checkout:" re-baselines quietly for exactly one generation; porcelain-clean resurrection via stat.
- **Impact cascade** — `impact-cascade.md`: reasons attach per NODE (hunks), files aggregate for display; seedMass normalizes cascade comparison across repo sizes.
- **Ops loop** — `four-ops-disclosure-loop.md`: sketch t=16 / focus t=2 / dwell ×factor≤64 / impact t=4 share one disclosure ledger; fresh restarts sharp; tests discounted in silhouettes.
- **Provenance journals** — `mutation-provenance-journals.md`: `captureMutation`/`recordMutationTransitions` — per-session tmpdir JSON journals, pid+uuid temp rename publishes, no-op transitions dropped, readers drain in-flight writes first.
- **Ownership lattice** — `sha-transition-ownership-lattice.md`: `attributeChanges`/`ownersForTransition` — reachability over hash transitions; co-edited chains classify mixed BY CONSTRUCT; unreachable edges ignored.
- **Delivery routing** — `provenance-delivery-routing.md`: kind→delivery — `other-session` ⇒ next-prompt notice, everything else steers now; Origin line names the actor class.
- **Nested disclosure** — `progressive-nested-disclosure.md`: enrolled `.git`-marker boundaries; first-edit hint or collapsed gitlink drift enrolls the parent CHAIN; vanished markers purge facts; enrollment survives restarts via cache header.
- **Outside attention** — `outside-attention-rebaseline.md`: all-drift-out-of-scope ⇒ silent snapshot adoption preserving heat/warmthArmed/pushed; structural ack with ignoredFiles; follow-up sync sees nothing.
- **Fact-pass chain** — `fact-pass-chain.md`: `factPass` — 8-line never-rejecting serializer; correctness (failure-ledger misattribution) + survival (spawn pileup) demand it.
- **Generated skip** — `generated-source-skip.md`: `isGeneratedSource` — name convention OR ≥4k-char line; empty-but-cached facts, own report bucket, not taint; self-heals on content change.
- **Agent-dir shim** — `agent-dir-shim.md`: `resolveAgentDir` — deliberate duplication of host path resolution to dodge module-graph reload tax; `PI_CODING_AGENT_DIR` override pinned by settings tests.
- **astgrep rule-scan runner** — `astgrep-rule-scan-runner`: how do you evaluate many structural patterns over many files through ONE external CLI without version drift or partial-trust results.
- **Consolidated fact scan** — `consolidated-fact-scan`: how do imports, calls, and string literals all come out of ONE pattern pass instead of three separate sweeps.
- **Git porcelain oracle** — `git-porcelain-oracle`: how do you answer "what drifted?" in one cheap probe without ever trusting a partially-parsed result.
- **Graph project re-registration** — `graph-project-reregistration`: how do you keep a foundation leaf's Retrieve surface alive when the codebase-memory indexer re-registers the same repo under a new path-slugged project name.
- **Language routing tables** — `language-routing-tables`: which parser tier does a file get, and how does an old extractor version fail honestly.
- **Literal site harvest** — `literal-site-harvest`: where do joinable literal SITES come from before the join index, and how do non-code config files join the graph.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Each new capsule must carry Path/Symbol, Signature, Data Shape, a labelled decisive source excerpt, Flow, Invariant, a direct-test Probe, and a `search_graph` Retrieve.

## Provenance
pi-fovea (MIT), `main@5bd4e6f5c56190fb174245266464607b11f7a337` (release 0.18.3); Codebase Memory project `mnt-hdd-utopia-inspo-pi-fovea` (984 nodes / 3,106 edges, FULL mode, ready, zero parse_partial/skipped; only `media/cover.svg` excluded by design — re-registered under this name on 2026-08-26, see Pass 4). Pass 1 squeezed release 0.14.3 `DETACHED@217a103` against the pre-drift short-name project `pi-fovea` (871n/2605e; entry [DONE:152]). Pass 2 re-entered after upstream advanced 23 commits (v0.14.3→v0.18.3): the refreshed graph lives under the path-slugged TWIN project named above (refresh-in-place is impossible through the old symlinked registration; stale-twin protocol) and all pass-2 Retrieve blocks cite the twin. Pass-2 whole-file reads: provenance.ts, graph.ts, state.ts, sync.ts, session.ts, agent-dir.ts, git.ts, plus drifted regions of build.ts (cache v11, generated skip, enrolled listing), extract.ts (scan consolidation), anchors.ts (implicit-flag threading), astgrep.ts, index.ts (lazy loads, sessionId wiring); direct-test reads: provenance.test.ts, workspace.test.ts, generated.test.ts, extension.test.ts, report.test.ts, sync.test.ts. All 12 cited paths report `no_recorded_issue`. Full vitest suite passes 160/160 at HEAD (was 135 at the pass-1 pin). Pass 3 (2026-08-24, closure-hold full-leaf audit at UNCHANGED pin `main@5bd4e6f`, zero upstream drift ls-remote-verified): real vitest runner re-executed 160/160 GREEN; static test-title anchors verified against live inventories across all cited suites; body-level claims spot-checked against source (`buildCsr` max-conductance symmetrization :36-64, join df∈[2,48] gate :50/:91, discover p̂≥0.55 cliff :115, config 99999→8192 clamp :102/:109); ALL 29 Retrieve blocks now cite the twin uniformly (the 20 pass-1-carried capsules still named the stale short-name project `pi-fovea` — repaired this pass; that stale registration serves the pre-drift 871n/2605e v0.14.3 graph through a LIVE SYMLINK root, so it resolves real-but-stale bytes rather than erroring — the dangerous silent class); one dead query repaired (`outsideAttention ignoredFiles attentionScopes` → BM25-zero → re-derived `outsideAttention ignoredFiles sync`, total:49 live-verified); hybrid-grep-router's coverage caveat corrected — extension.test.ts exercises the registered grep tool end-to-end in five direct tests, caveat narrowed to session-middleware wiring only.

Pass 4 (2026-08-26, miner-pi-fovea lane FAC-87, UNCHANGED pin `main@5bd4e6f5c561`, tree clean): the pass-2/3 twin registration `mnt-hdd-utopia-inspo-pi-ecosystem-pi-fovea` had VANISHED from `list_projects`; a fresh FULL re-index of the same checkout re-registered the graph as the path-slugged twin `mnt-hdd-utopia-inspo-pi-fovea` (984n/3106e — the 3104→3106 edge delta is indexer-version drift at identical HEAD; legacy short-name `pi-fovea` 871n/2605e still serves the pre-drift v0.14.3 parse). All 29 reference Retrieve/Source citations retargeted to the live twin (grep-verified zero dead-name remnants outside the historical reregistration capsule); detection ladder + repair protocol captured as `./graph-project-reregistration.md`. Five genuinely uncited seams mined whole-file this pass: astgrep rule-scan runner, consolidated fact scan, literal-site harvest, language-routing tables, git porcelain oracle (`astgrep-rule-scan-runner.md`, `consolidated-fact-scan.md`, `literal-site-harvest.md`, `language-routing-tables.md`, `git-porcelain-oracle.md`), each with executed vitest Probes (extract/sync suites GREEN at HEAD) and live search_graph Retrieves on the live twin. Known residual: ~14 carried capsules still carry pass-1-era `DETACHED@217a103` Source-pin lines whose bodies were verified against main@5bd4e6f in passes 2–3 — mechanical pin-line refresh is the standing next-pass item.

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-pi-fovea` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. The graph was re-indexed at `main@5bd4e6f`; if upstream advances past that pin, expect ANOTHER path-slugged twin — verify which project carries the new head_sha before citing (see `./graph-project-reregistration.md`). Every Retrieve block in every reference cites the live twin uniformly (pass-4 audit repair). Note: `tests/settings.test.ts` covers settings/grepMode plumbing; the registered grep tool's routing behavior is covered end-to-end by `tests/extension.test.ts` (five direct tests), while pi session-middleware wiring of the hybrid router remains host-integration surface (caveat recorded in its capsule).

## Boundaries
Adopt the diffusion kernel + CSR operator, budget-hard foveated rendering, literal-join bridging, the anchor rule pack + discovery promotion, the honest fact cache, the sync verdict algebra, co-change overlays, basins, fuzzy seed resolution, the scheduling kernel, the provenance journal + ownership-lattice attribution pair, delivery-channel gating, progressive nested disclosure, outside-attention silent rebaselines, the fact-pass serialization chain, and the generated-source tripwire — these are portable contracts with direct-test pins. Adapt edge weights/tier constants/thresholds (measured against this repo's fixtures — recalibrate on your graphs), the config key names, the tmpdir journal retention knobs, the pi hook wiring (`deliverAs:"steer"`, `triggerTurn`, `tool_result` middleware, sessionId plumbing), and the ast-grep CLI invocation details to your host. Omit the TUI command surfaces (`/fovea *` handlers, settings UI), the published-CLI packaging plane (`cli.ts`, scripts/, knip), and the fabric-proxy integration notes unless your host is pi-fabric.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`agent-dir-shim.md`](./agent-dir-shim.md)
- [`anchor-hub-collapse.md`](./anchor-hub-collapse.md)
- [`astgrep-rule-scan-runner.md`](./astgrep-rule-scan-runner.md)
- [`basins-feature-regions.md`](./basins-feature-regions.md)
- [`cochange-history-overlay.md`](./cochange-history-overlay.md)
- [`conductance-csr.md`](./conductance-csr.md)
- [`config-two-scope-model.md`](./config-two-scope-model.md)
- [`consolidated-fact-scan.md`](./consolidated-fact-scan.md)
- [`discovered-route-rules.md`](./discovered-route-rules.md)
- [`fact-pass-chain.md`](./fact-pass-chain.md)
- [`file-source-overlay.md`](./file-source-overlay.md)
- [`four-ops-disclosure-loop.md`](./four-ops-disclosure-loop.md)
- [`foveated-budget-renderer.md`](./foveated-budget-renderer.md)
- [`fuzzy-seed-resolution.md`](./fuzzy-seed-resolution.md)
- [`generated-source-skip.md`](./generated-source-skip.md)
- [`git-porcelain-oracle.md`](./git-porcelain-oracle.md)
- [`graph-project-reregistration.md`](./graph-project-reregistration.md)
- [`heat-kernel-chebyshev.md`](./heat-kernel-chebyshev.md)
- [`honest-fact-cache.md`](./honest-fact-cache.md)
- [`hybrid-grep-router.md`](./hybrid-grep-router.md)
- [`impact-cascade.md`](./impact-cascade.md)
- [`import-resolution.md`](./import-resolution.md)
- [`language-routing-tables.md`](./language-routing-tables.md)
- [`literal-join-index.md`](./literal-join-index.md)
- [`literal-site-harvest.md`](./literal-site-harvest.md)
- [`mutation-provenance-journals.md`](./mutation-provenance-journals.md)
- [`outside-attention-rebaseline.md`](./outside-attention-rebaseline.md)
- [`progressive-nested-disclosure.md`](./progressive-nested-disclosure.md)
- [`provenance-delivery-routing.md`](./provenance-delivery-routing.md)
- [`route-anchor-pack.md`](./route-anchor-pack.md)
- [`session-reload-state.md`](./session-reload-state.md)
- [`sha-transition-ownership-lattice.md`](./sha-transition-ownership-lattice.md)
- [`state-lifecycle-checkout.md`](./state-lifecycle-checkout.md)
- [`sync-surprise-gate.md`](./sync-surprise-gate.md)
- [`tui-safe-scheduling.md`](./tui-safe-scheduling.md)
- [`warm-defer-sync-pipeline.md`](./warm-defer-sync-pipeline.md)
