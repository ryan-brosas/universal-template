<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Pi Fabric Foundation

## Use this for
Porting Pi Fabric's supervisor/runtime internals: per-actor single-flight drains, stop-the-world interrupts, cross-host ownership of a shared registry, sandboxed activation predicates, transport-agnostic worker launching with startup-retry classification, cross-provider trajectory handoffs, LLM-assisted approval gating, append-only budget ledgers, a resident (outliving-the-UI) host protocol, QuickJS guest embedding, hardened POSIX file ops, plus the schema mutation guard, prewalk handoff state machine, mesh store, memory discovery, compaction bounds, and transcript sanitization. Deeper planes cover the prewalk boundary execution choreography (claim precedence, continuation identity, compact-before-restore settle), per-backend terminal transports (multiplexer twins, herdr socket client, localterm pid liveness), the spawned-worker child contract (strict argv grammar, crash-safe run records), bounded rendering (per-section byte-budgeted summary render, write-diff skip gates, preview-carrying writes), and transport-exit supervision (sustained-dead windows feeding an error-string retry protocol). Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval. Deepest planes cover the repo's own proof machinery — deterministic certification ladders over its compaction/memory/handoff stack, address-routed continuation oracles, an opt-in billable benchmark gate with Wilson-interval paired reporting, and the durable state-layer kernel (two-phase CAS transitions with compensating rollback plus self-non-staling current certificates).

## Load the matching source dump
- `./architecture.md` — the Schema mutation guard (authorize → hypothesize → verify → commit with journaled recovery).
- `./actor-drain-single-flight.md` — one drain loop per actor without stranding an item in the microtask window.
- `./actor-stop-the-world-halt.md` — interrupt every actor; only the user's next message re-arms dispatch.
- `./actor-validwhile-sandbox.md` — untrusted activation predicates in QuickJS: frozen facts, deny-all tools, sync-only.
- `./actor-ownership-ladder.md` — five-rule ownership decision plus abort-and-reject handoff across hosts.
- `./actor-delivery-policy-triad.md` — steer/followUp/mailbox/nextTurn with construction-time triggerTurn validation.
- `./veda-headless-runner-contract.md` — one-shot headless CLI child: stdin task, minimal argv, envelope normalization, per-run session isolation.
- `./agent-transport-family.md` — process/tmux/screen/localterm/herdr behind one adapter interface; auto ladder order.
- `./agent-runtime-and-retry.md` — runtime resolution under a bundled binary; zero-progress retry gate; sustained-dead liveness.
- `./call-time-capability-rejection.md` — unsupported-operation guards that throw before any side effect; mode setters stay ungated.
- `./agent-thinking-transfer.md` — preserved/re-signed/stripped thinking across model families; clone-not-mutate session materialization.
- `./headless-envelope-error-laundering.md` — drain error + per-protocol gate fields into one terminal error without erasing partial output.
- `./core-approval-ladder.md` — policy→inherited→session grants→LLM classifier, fail-closed everywhere.
- `./agents-budget-ledger.md` — env-propagated append-only spend ledger for a process tree; documented overshoot race.
- `./resident-host-protocol.md` — rename-claim request dirs, indeterminate-outcome recovery, token-guarded locks.
- `./runtime-quickjs-guest-kernel.md` — host-call bridge, monotone deadline extension, grace-window teardown.
- `./core-file-ops-hardening.md` — atomic writes, rename/rm retry classes, reverse JSONL pager, pid-liveness pattern.
- `./prewalk.md` — plan-first handoff state machine (arm → claim-on-mutation → continuation settle).
- `./mesh-store.md` — append-only bounded event log + key-version CAS state + lock coordination.
- `./memory-discovery.md` — session enumeration and scope resolution (session/project/global, ambiguity-guarded).
- `./compaction-bounds.md` — UTF-8-safe clipping, canonicalization, provenance-preserving earliest+latest sampling.
- `./ux.md` — transcript sanitization as a security surface (escape/bidi defense, grapheme-safe clip, secret redaction).
- `./core-tool-capture.md` — prototype-hub observation of every registered tool without filtering the host registry.
- `./core-tool-lifecycle.md` — active-set ownership with index-faithful restore; nested-failure laundering to the outer result.
- `./core-tool-result-proxy.md` — middleware round trip for nested tool_results (isError-throw > details swap > content patch).
- `./actor-global-registry.md` — machine-global actor template store: identity stripped on export, defensive reload.
- `./core-capability-combustion.md` — once-per-source prompt advisories: ash burn, warmth EWMA, smoke feedback.
- `./memory-lineage.md` — active-branch scoping of session JSONL via leaf-anchored parent walk + lineage fingerprint.
- `./memory-digest-fold.md` — bounded honest vocabulary + complete structural addresses + explicit coverage reasons.
- `./memory-bounded-regex.md` — untrusted regex in a disposable heap-capped worker; explicit-mode query planning.
- `./residency-client.md` — file-based command/response to the resident host with liveness-checked waits.
- `./compaction-continuity-cut.md` — min-of-four-constraints cut target; closure-safe boundaries that never orphan a tool pair.
- `./core-evidence-runner.md` — hash-all/retain-prefix shell evidence with process-group kill.
- `./core-abortable-settlement.md` — runAbortable/settleWithin micro-kernel: single-settlement, no listener leaks.
- `./audit-trace-envelope.md` — execution trace V1 recorder: seal-time outcome laundering, counted losses, 512 KiB shrink ladder.
- `./audit-allowlist-projection.md` — exact-ref default-deny projection of invocation args/results.
- `./audit-persisted-details-budget.md` — aggregate-bound details shrinking plus legacy-wins render bridging.
- `./audit-sanitization-ladder.md` — walk-time key-class redaction then measured prefix-fit bounding of arbitrary values.
- `./memory-tiered-index.md` — hot shards / cold digests under byte budgets; self-describing cache validation; TOCTOU double fingerprint.
- `./memory-search-assembly.md` — five-mode search dispatch, boundary-flushed segments, cold-pointer hydrate recipe.
- `./memory-trace-ingestion.md` — nested fabric operations become independently searchable entries with exact structural fields.
- `./topology-participant-directory.md` — hashed-key presence records, host-lease staleness, CAS takeover, quiesce-then-close.
- `./topology-refresh-lifecycle.md` — single-flight refresh coalescing with trailing-edge re-arm and heartbeat recovery.
- `./compaction-projection-folds.md` — pure section folds with typed identity keys and addressed omissions.
- `./compaction-typed-instructions.md` — magic-prefix typed compaction requests decoded by a strict hand-rolled JSON parser.
- `./compaction-enricher-seam.md` — zero-builtin enricher registry for deterministic prose annotation.
- `./topology-control-plane-exactly-once.md` — exactly-once steer/stop commands over an at-least-once mesh log.
- `./lifecycle-broker-cursor-subscriptions.md` — durable subscription cursors with per-event ownership re-checks.
- `./config-migration-ladder.md` — version-stepped config migrations with canonical-wins merges and fail-loud rungs.
- `./topology-participant-projection.md` — state-derived capability sets for agent/actor participant records.
- `./action-registry-invoke-stages.md` — guard → prepare → validate → approve → invoke stage machine with audit/trace.
- `./action-registry-merkle-catalog.md` — deterministic Merkle capability catalog over sorted descriptor hashes.
- `./direct-tool-approval-bridge.md` — risk/approval bridging for uncaptured pi/extension tools without wrapping them.
- `./nested-agent-skill-rewiring.md` — skill catalog restore, `<skill-dir>` expansion, and cross-skill reference guidance in nested prompts.
- `./fabric-exec-result-assembly.md` — output budgeting with artifact spill, media re-attachment, terminate/handoff settlement.
- `./fabric-exec-boundary-repairs.md` — flat-schema policy plus display/code/null near-miss repairs pre-validation.
- `./agent-semaphore-abortable-gate.md` — FIFO permit-passing semaphore with queued-waiter abort.
- `./main-agent-identity-delivery.md` — env-ladder identity resolution (actor > recursive agent > main) and local-gated delivery to the root Main target.
- `./fabric-state-assembly-ladder.md` — construct→gate→start→mirror-close ordering for every kernel; execution service as readiness signal; enforce-mode clone gating.
- `./execution-service-host-call-switch.md` — single host-call dispatch where agent budgets, full-code walls, deadline floors, handoff deferral, and trace stages wrap every nested call.
- `./runtime-orchestration-deadline-classifier.md` — static call-site regex + dynamic blocking-ref set grant the long deadline only to programs that block on child agents.
- `./runtime-node-process-escape-hatch.md` — process-per-program trusted runtime: monotone deadline extension, bounded host-call settlement, OOM-as-runtime-error.
- `./runtime-functional-type-gate.md` — functional-errors-only TypeScript gate over an in-memory two-file compiler host; emitted JS feeds the sandbox.
- `./extension-entry-composition.md` — hook-to-concern wiring: ESC stop-the-world debounce, turn-scoped ownership reassertion, message_end handoff boundary.
- `./compact-intent-single-slot.md` — model-requested compaction as one replaceable intent slot that only the host commits at agent_settled.
- `./child-compact-control-plane.md` — parent-driven child compaction over RPC with an order-independent two-event shutdown handshake.
- `./compaction-reconstruction-qa.md` — deterministic LLM-free grading of summaries via ground-truth probes with addressed omissions.
- `./branch-summary-versioned-envelope.md` — strict per-version summary envelopes behind one union reader; byte/node budgets enforced at validation.
- `./actor-context-digest.md` — cheap byte-stable digest plus bounded oldest-drop transcript for actors observing host sessions.
- `./host-event-payload-redactor.md` — single-pass persistence sanitizer: key-class + inline secrets, base64 omission, sha256 image hoisting.
- `./prewalk-arm-command-surface.md` — slash-command arming of next-turn behavior with branch-deduplicated hidden advisories.
- `./temp-run-root-retention.md` — owner-file run-root GC with PID liveness, first-sighting orphan stamps, and terminal-run clocks.
- `./lexical-complexity-token-fold.md` — parser-free statement-decision counting with regex/JSX-safe scanning feeding per-file delta ledgers.
- `./git-worktree-lease.md` — id-keyed worktree leases giving sub-agents isolated checkouts with timeout-guarded cleanup.
- `./pi-host-compatibility-gate.md` — realpath package-walk host detection with prerelease-aware version-floor warnings naming the broken capability.
- `./headline-argument-picker.md` — priority-key then skip-list headline selection for arbitrary tool-call previews.
- `./participant-routing-ladder.md` — four-arm steer/followUp resolution (Main alias → local agent → actor mailbox → mesh peer) with capability gating and a loud no-broadcast throw.
- `./inbound-control-boundary.md` — mirrored acceptControl ladder answering remote steer/followUp/stop with explicit typed refusals naming ownership conflicts.
- `./bounded-progress-preview-pump.md` — settled-latch 1s progress timer + revision-deduped, depth/node-budgeted child-tool preview tree.
- `./durable-actor-activation-compensation.md` — cede→refresh→ensureActor transfer to the resident host with remove-before-reclaim rollback.
- `./runner-capability-partition.md` — per-runner legality enforced at one coercion layer: veda actors throw, handoff pins pi, model catalogs are advisory.
- `./actor-privacy-status-cascade.md` — owner-gated private actor reads and the five-source typed-sentinel status/log/stop resolution cascade.
- `./activity-ledger-bounded-store.md` — bounded in-memory run/call/item/event ledger: strict directed writes vs silent streaming writes, clone-on-read isolation, running-first pruning, fabricTruncated payload envelopes.
- `./model-keyed-compaction-thresholds.md` — per-model token/ratio thresholds on one canonical provider/id key; cancel-to-defer hook over the host auto-compactor; token beats ratio.
- `./thinking-level-plumbing.md` — one ordered 7-value effort enum validated at every boundary; resolved once (request ?? config); translated only at the CLI edge (claude off/minimal→low).
- `./residency-digest-deliveries.md` — SHA-256(rootId)-derived host/dir/delivery namespaces; validate-every-field drain of mesh deliveries with authorship gate and ifVersion CAS delete.
- `./compaction-normalization-contract.md` — structural-only session→typed-event normalization: stable 1-based indices, id-keyed result pairing, branch-fact replay, mirrored erased-thinking counter.
- `./prewalk-boundary-execution-plane.md` — claim/run/settle choreography at the outer tool-result boundary: explicit-request precedence, identity-filtered continuations, compact-before-restore, result-not-throw errors.
- `./tmux-screen-session-twins.md` — classic multiplexer launch twins: shared name scheme, per-tool creation grammar (string vs argv), fail-soft CLI liveness probes.
- `./herdr-socket-client.md` — newline-JSON socket client with 3s timeout, 1MB frame cap, single-settlement latch, argv-array pane payloads.
- `./localterm-pid-liveness.md` — JSON-handshake session launch whose liveness is a local pid probe instead of repeated CLI calls.
- `./transport-exit-supervision.md` — sustained-dead window → laundered error-string protocol → zero-progress retry gate over dying transports.
- `./worker-options-contract.md` — even-slot argv pair grammar for spawned workers: required/optional lanes, runner whitelist at the child boundary, loud parse-time death.
- `./worker-run-record-plane.md` — pid-temp atomic status writes with rename-retry, crash-record synthesis, and apply/delta usage attribution.
- `./compaction-summary-render.md` — fixed-section summary renderer where every section fits its byte cap via line sampling and a final whole-document clip.
- `./write-diff-size-guards.md` — cumulative byte ceiling + changed-line-cell product gates in an import-isolated pure module.
- `./write-preview-tool-wrapper.md` — read-before-write preview capture under the host's per-file mutation queue with typed skip envelopes.
- `./certification-rpc-benchmark-gate.md` — opt-in billable A/B benchmark: all-reasons fail-closed env gate, credential name-not-value, seeded paired arm orders, Wilson 95% intervals.
- `./certification-threshold-ladder.md` — 24 named sabotage-testable checks; last-20 steady window bounded by range AND least-squares slope to catch late growth.
- `./deterministic-continuation-oracle.md` — address-routed CERT_TASK_V1 replay after integrity-bound expansion; static-first fixture grading before any spawned test.
- `./version-pinned-hook-mirror-harness.md` — exact-version + function-shape pin over an unexported internal API; Proxy-counted previousSummary reads measure hook behavior.
- `./state-transition-two-phase-commit.md` — proposal→ledgers→pending-head→marker→proof-upgrade ladder; reverse-order compensation forbidden after the marker.
- `./state-certificate-binding.md` — certificate pre-bound to the CAS's own post-write version; identity-gated revocation before violation publication.
- `./bench-pier-paired-comparison.md` — external eval jobs paired by start-order rep index with strict key-set equality; unmatched corpora fail loudly.

## Capsule map
- **Mutation guard** — `architecture`: authorize/hypothesize/verify/commit, allowlist, journaled recovery.
- **Actor supervision** — `actor-drain-single-flight`, `actor-stop-the-world-halt`, `actor-global-registry`: single-flight queue consumer; ESC latch lifted only by input; machine-global template registry with identity-stripped export.
- **Actor safety & identity** — `actor-validwhile-sandbox`, `actor-ownership-ladder`, `actor-delivery-policy-triad`: sandboxed conditions, five-rule ownership, four-mode delivery.
- **Agent launching** — `agent-transport-family`, `agent-runtime-and-retry`: five backends behind one handle contract; bundled-runtime ladder + startup-retry classification. `veda-headless-runner-contract` extends the family with the one-shot headless dialect (stdin task, argv builder, envelope normalization, per-run session isolation).
- **Trajectory & cost** — `agent-thinking-transfer`, `agents-budget-ledger`: three-policy thinking transfer; O_APPEND budget tree.
- **Supervisor process** — `resident-host-protocol`: crash-safe three-directory file protocol for durable hosting.
- **Sandboxing & security** — `runtime-quickjs-guest-kernel`, `core-approval-ladder`, `ux`: guest bridge with deadline/settlement discipline; fail-closed risk approvals; layered output sanitization.
- **Infra kernels** — `core-file-ops-hardening`: atomic write / rm retry / JSONL tail / liveness probe primitives.
- **Coordination stores** — `mesh-store`, `memory-discovery`: bounded event log + CAS state; scoped session enumeration.
- **Context lifecycle** — `compaction-bounds`, `compaction-continuity-cut`, `prewalk`: byte-safe clipping/sampling; calibrated four-constraint cut budget with closure-safe boundaries; arm→claim-on-mutation handoff FSM.
- **Tool capture & ownership** — `core-tool-capture`, `core-tool-lifecycle`, `core-tool-result-proxy`: observe-only registry mirroring; active-set swap/restore + failure laundering; middleware patch precedence.
- **Capability advisory** — `core-capability-combustion`: tf-idf fingerprints, 1/df scoring, ash/warmth/smoke ignition discipline.
- **Memory indexing** — `memory-lineage`, `memory-digest-fold`, `memory-bounded-regex`: branch-scoped lineage; bounded digest fold; sandboxed regex execution.
- **Verification & settlement** — `core-evidence-runner`, `core-abortable-settlement`: hash-covered command evidence; abort/settle micro-kernel.
- **Residency (client side)** — `residency-client`: request/response files, liveness-checked waits, delivery drain.
- **Execution audit** — `audit-trace-envelope`, `audit-allowlist-projection`, `audit-sanitization-ladder`, `audit-persisted-details-budget`: bounded V1 trace recorder; default-deny projection; value sanitization; aggregate-bound persisted details with legacy rendering.
- **Memory orchestration** — `memory-tiered-index`, `memory-search-assembly`, `memory-trace-ingestion`: tiered shard/digest caching; five-mode search with honest coverage; nested-operation ingestion.
- **Topology presence** — `topology-participant-directory`, `topology-refresh-lifecycle`: lease-guarded multi-host presence; coalesced single-flight refresh lifecycle.
- **Compaction engine** — `compaction-projection-folds`, `compaction-typed-instructions`, `compaction-enricher-seam`: deterministic section folds; strict typed instruction channel; zero-builtin enricher seam.
- **Command & event fabric** — `topology-control-plane-exactly-once`, `lifecycle-broker-cursor-subscriptions`, `topology-participant-projection`: exactly-once commands with durable seen-claims; persisted-cursor subscriptions with ownership re-checks; capability-derived participant records.
- **Config evolution** — `config-migration-ladder`: version-stepped document migration with fail-loud ambiguity handling.
- **Action registry** — `action-registry-invoke-stages`, `action-registry-merkle-catalog`: six-stage nested invocation machine; deterministic hash-addressed capability catalog.
- **fabric_exec boundary** — `fabric-exec-boundary-repairs`, `nested-agent-skill-rewiring`: flat-schema near-miss repairs pre-validation; skill catalog/dir-marker/reference rewiring for promptless sub-agents.
- **Result assembly** — `fabric-exec-result-assembly`, `direct-tool-approval-bridge`, `agent-semaphore-abortable-gate`: budgeted output with artifact spill and media re-attachment; approval bridging for uncaptured tools; abortable FIFO concurrency gate. `call-time-capability-rejection` + `headless-envelope-error-laundering` guard the child boundary: throw-before-side-effect for unsupported runner operations, multi-channel error collection that never erases partial output.
- **Composition roots** — `main-agent-identity-delivery`, `fabric-state-assembly-ladder`, `extension-entry-composition`: identity ladder + local-gated Main delivery; kernel assembly/shutdown ordering; lifecycle-hook choreography with ESC debounce and handoff boundary.
- **Execution spine & runtime pair** — `execution-service-host-call-switch`, `runtime-orchestration-deadline-classifier`, `runtime-node-process-escape-hatch`, `runtime-functional-type-gate`: one guarded host-call dispatch; static+dynamic deadline classification; trusted Node-process runtime; functional-errors-only type gate feeding emitted JS.
- **Compaction control plane** — `compact-intent-single-slot`, `child-compact-control-plane`, `compaction-reconstruction-qa`, `branch-summary-versioned-envelope`: single-slot model intents committed by the host; order-independent two-event child shutdown; ground-truth probe grading with addressed omissions; strict versioned summary envelopes.
- **Actor observation plane** — `actor-context-digest`, `host-event-payload-redactor`, `prewalk-arm-command-surface`: byte-stable session digests; one-pass secret/media-safe payload sanitization; deduplicated next-turn arming from the command surface.
- **Ops kernels** — `temp-run-root-retention`, `lexical-complexity-token-fold`, `git-worktree-lease`, `pi-host-compatibility-gate`, `headline-argument-picker`: owner-file run-root GC; parser-free complexity deltas over ledgered files; worktree checkout leases; prerelease-aware host version gate; generic call-preview headlines.
- **Agents-provider action surface** — `participant-routing-ladder`, `inbound-control-boundary`, `bounded-progress-preview-pump`, `durable-actor-activation-compensation`, `runner-capability-partition`, `actor-privacy-status-cascade`: one provider layer routing every participant message with typed no-broadcast failure, mirrored inbound control refusals, budgeted progress previews on a settled-latch timer, compensated durable-actor ownership transfer, per-runner capability throws at coercion time, and owner-gated private reads behind a five-source status cascade.
- **Observability & effort planes** — `activity-ledger-bounded-store`, `model-keyed-compaction-thresholds`, `thinking-level-plumbing`: bounded clone-on-read activity ledger with strict-vs-silent write tiers; per-model compaction thresholds enforced through a cancel-to-defer hook; one validated effort enum plumbed default→config→request→runner-argv.
- **Residency delivery & normalization contracts** — `residency-digest-deliveries`, `compaction-normalization-contract`: rootId-digest mailbox namespaces with field-complete drain validation and CAS deletes; structural-only typed-event normalization with stable indices, id pairing, branch-fact replay, and audited thinking erasure.
- **Prewalk boundary execution** — `prewalk-boundary-execution-plane`: the execute-side half of the prewalk FSM at the outer message_end boundary — claim precedence over armed tasks, continuation identity filtering (trajectory bypass), compact-before-restore settle ordering, result-not-throw error envelopes, and post-truncation re-arm directives.
- **Terminal transports deep plane** — `tmux-screen-session-twins`, `herdr-socket-client`, `localterm-pid-liveness`: per-backend launch grammars and liveness disciplines behind the family adapter — CLI probes for tmux/screen, a single-settlement newline-JSON socket client for herdr, pid-based liveness for localterm.
- **Worker child contract** — `worker-options-contract`, `worker-run-record-plane`: the spawned worker's even-slot argv schema with boundary-side runner whitelisting, plus crash-safe atomic status publishing and dual cumulative/delta usage attribution.
- **Bounded rendering & preview gates** — `compaction-summary-render`, `write-diff-size-guards`, `write-preview-tool-wrapper`: per-section byte budgets with addressed line sampling; import-isolated diff-skip guards (byte ceiling + changed-cell product); read-before-write preview capture under a per-file mutation queue.
- **Transport supervision** — `transport-exit-supervision`: sustained-dead liveness windows, laundered error-string protocol consumed by the zero-progress retry gate, and log-tail diagnosis embedded in failure records.
- **Evaluation & certification plane** — `certification-rpc-benchmark-gate`, `certification-threshold-ladder`, `deterministic-continuation-oracle`, `version-pinned-hook-mirror-harness`: how the repo proves its own compaction/memory/handoff stack with deterministic oracles — a skip-by-default billable benchmark gate with paired-order randomization and Wilson intervals, a named-check endurance ladder with dual steady-window drift bounds, an address-routed no-model continuation replay graded static-first, and an honest mirror over Pi's unexported compaction internals with measured previous-summary access.
- **State-layer durable kernel** — `state-transition-two-phase-commit`, `state-certificate-binding`: the uncited core of `src/state/store.ts` — two-phase pending→committed CAS heads with captured-before compensation and version-aware deleted keys, plus current-certificate persistence that pre-binds its own post-write version and revokes identity-gated before publishing violations.
- **External eval analytics** — `bench-pier-paired-comparison`: the Python half of evaluation — matched-pairs comparison of external agent-eval job trees that refuses to average unmatched trials.

## Extending the foundation
Add one `./<seam>.md` capsule-v2 for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-fabric (MIT), `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory project `pi-fabric` (canonical root `$REFERENCE_ROOT/pi-ecosystem/pi-fabric`; 5,650 nodes / 25,044 edges @ pass-7 re-index; parse_partial ×1: `tests/auto-approval-classifier.test.ts:8`; `.pi/fabric/mesh` + dist + `.veda` excluded by design — upstream e9894f0 gitignored `.veda/`, removing the former design.xml parse-partial from the index). Pass 2 deepening (2026-08-24) added 12 capsules at the SAME pin; Pass 3 (2026-08-24) added 14 more at the same pin — audit plane, memory orchestration above the captured kernels, participant directory, compaction engine; Pass 4 (2026-08-24) added 10 more at the same pin via citation-vs-inventory sweep — command/event fabric, action registry, fabric_exec boundary/result assembly, skill rewiring, approval bridge; Pass 5 (2026-08-24) added 7 more at the same pin under the composition/wiring question — main-agent identity, FabricState assembly ladder, execution-service host-call switch, orchestration deadline classifier, Node-process escape hatch, functional type gate, extension-entry composition; Pass 6 (2026-08-24) added 12 more at the same pin via a fresh file-granular citation-vs-inventory census under the compaction-control/actor-observation/ops-kernel questions — compact intent slot, child compact control, reconstruction QA, versioned summary envelopes, actor context digest, host event payload redactor, prewalk arm command surface, temp run-root retention, lexical complexity token fold, git worktree lease, Pi host compatibility gate, headline argument picker; Pass 7 (2026-08-24) re-entered on genuine upstream drift (`fork` remote 06a13dd→e9894f0, local rebased to `4874ac3a`) — pulled with autostash preserving the dead Aug-13 jetbrains WIP, re-indexed in place through the live-symlink root (5,703n→5,650n; `.veda` now excluded by design), repaired the budget capsule's drift-shifted manager.ts anchors, and added 3 capsules under the headless-runner-boundary question — veda-headless-runner-contract (stdin-task argv builder + envelope normalization + per-run session isolation), call-time-capability-rejection (#requireSteerable throws before any side effect; mode setters deliberately ungated), headless-envelope-error-laundering (error + design/worker gate fields drain into one terminal error while partial output persists); `core-abortable-settlement`, `agent-semaphore-abortable-gate`, and `topology-participant-projection` have no dedicated direct test files (exercised via consumer tests or source pins — coverage caveats recorded in those capsules), and `compaction-enricher-seam` likewise has no dedicated upstream suite (consumer-tested caveat in-capsule); the media re-attachment plane is pinned by in-source comments only. Pass 8 (2026-08-24, same pin, zero upstream drift) opened the never-mined providers plane at its hub `src/providers/agents-provider.ts` (1,970L read whole-file) under the queued provider-binding question and added 6 capsules in the NEW map group **Agents-provider action surface** — participant-routing-ladder (four-arm Main→local-agent→actor→mesh resolution with capability gating; unknown ids throw, never broadcast), inbound-control-boundary (acceptControl mirrors the ladder with explicit `{accepted:false,error}` refusals; ownership conflicts name the owning host — refusal branches have NO direct test, source-only coverage caveat recorded), bounded-progress-preview-pump (settled-latch 1s timer, revision-string dedupe, depth≤4/nodes≤24 shared-budget preview tree with honest agentsTruncated flag; throwing progress callback fails the wait), durable-actor-activation-compensation (cede→refresh→ensureActor with remove-before-reclaim rollback; loud gate when residency is unavailable), runner-capability-partition (veda persistent-actor throw at coercion time, handoff force-pins runner=pi twice-gated on explicit model, only-longer timeout overrides honored), actor-privacy-status-cascade (#localActor owner+local dual gate; five-source status/log/stop ladders advancing ONLY on /Unknown Fabric (agent|actor)/ sentinels). Pass 9 (2026-08-24, same pin, zero upstream drift — `git fetch fork` + rev-list delta 0) ran the mandatory file-granular citation-vs-inventory census and mined the five remaining uncited non-UI seams under an observability-and-contracts question, adding 5 capsules in TWO new map groups **Observability & effort planes** and **Residency delivery & normalization contracts** — activity-ledger-bounded-store (strict directed writes throw vs silent streaming writes; clone-on-read; running-first prune; fabricTruncated envelopes), model-keyed-compaction-thresholds (one provider/id key gates both the proactive settled-turn compactor and the cancel-to-defer session_before_compact hook; token beats ratio), thinking-level-plumbing (7-value enum re-validated per boundary; resolved once request??config; translated only at the CLI edge: claude off/minimal→low), residency-digest-deliveries (sha256(rootId)-derived host/dir/prefix namespaces; field-complete drain validation incl. authorship; ifVersion CAS delete after delivery), compaction-normalization-contract (structural-only typed events with stable 1-based indices, id-keyed result pairing, branch-fact replay, mirrored erased-thinking counter; malformed custom entries skipped per-entry). Pass 10 (2026-08-24, same pin, zero upstream drift — `git fetch fork` + rev-list delta 0) re-ran the census at BASENAME granularity (catching that path-form greps missed bare-filename citations like the existing agent-transport-family capsule) and mined eight genuinely never-cited seams in FIVE new map groups **Prewalk boundary execution**, **Terminal transports deep plane**, **Worker child contract**, **Bounded rendering & preview gates**, and **Transport supervision** — prewalk-boundary-execution-plane (claim precedence over armed tasks, continuation identity filtering with trajectory bypass, compact-before-restore settle ordering, result-not-throw envelopes; tests/prewalk-handoff.test.ts 1,131L read whole), tmux-screen-session-twins (string-command vs argv-splice creation grammars; fail-soft CLI liveness), herdr-socket-client (newline-JSON over unix socket/win32 pipe, 3s timeout, 1MB cap, single-settlement latch; argv-array command payloads test-pinned), localterm-pid-liveness (strict JSON handshake validating id+pid; liveness via process.kill(pid,0), single-CLI-call contract log-pinned), worker-options-contract (even-slot argv pairs, 20 required lanes, runner whitelist at the child boundary), worker-run-record-plane (pid-temp atomic writes, Windows AV rename-retry ladder, crash-record synthesis, apply/delta usage duality), compaction-summary-render (per-section byte budgets, earliest+latest line sampling, final whole-document clip), write-diff-size-guards + write-preview-tool-wrapper (byte ceiling + changed-cell product gates in an import-isolated module; read-before-write preview under the host mutation queue), and transport-exit-supervision (1s sustained-dead window, error-string-as-retry-protocol coupling, zero-progress retry gate). Pass W1 / work-record epoch 1 (2026-08-25, same pin): the first pass with a durable work record (`inspo/pi-fabric-work/{state,research,verification}.md`; passes 1–10 above left none) and a ledger-row repair from stale pass-0; deep pass over the previously uncited evaluation-methodology and state-store planes added 7 capsule-v2 refs (certification-rpc-benchmark-gate, certification-threshold-ladder, deterministic-continuation-oracle, version-pinned-hook-mirror-harness, state-transition-two-phase-commit, state-certificate-binding, bench-pier-paired-comparison) with all three direct suites executed GREEN at this pin (tests/certification 16/16, tests/state-provider.test.ts 30/30, bench/test_analyze_pier.py 2/2); pre-W1 capsule probes citing `$REFERENCE_ROOT/pi-ecosystem/pi-fabric` must re-run against the post-move canonical root `$REFERENCE_ROOT/pi-fabric`.

## Full view (memory graph)
Revalidate `pi-fabric` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note: tool-layer credential redaction can mask `auth.apiKey`-shaped source text when reading `src/core/auto-approval-classifier.ts` — quote that range from git/disk, never from tool output.

## Boundaries
Adopt the supervision/launch/security contracts above plus the capture/ownership/advisory/memory/verification kernels, the audit/topology/command-fabric/action-registry/fabric_exec-boundary/result-assembly/composition-root/execution-spine contracts, the compaction-control/actor-observation planes, the ops kernels (retention, complexity, worktree lease, host gate, preview policy), and the agents-provider action surface (routing ladder, control boundary, preview pump, durable activation, runner partition, privacy cascade); adapt runner binaries, transport availability probes, delivery vocabulary, redaction budgets, combustion constants, presence lease timings, compaction line caps, retention windows, and complexity token sets to your host; omit the pi/Claude runner dialects (`src/agents/claude-cli.ts` argv mapping; `src/agents/veda-cli.ts` is NOW CAPSULED as the headless-runner contract — its former backend allowlist was removed upstream in 06a13dd, backends/models are pass-through), the remaining TUI/dashboard rendering internals (`src/ui/*` beyond sanitization + headline-arg preview policy + write-diff guard consumption — word-diff engine included), the remaining providers-plane files (`src/providers/{captured-tools,mcp,memory,mesh,schema,state,compact}-provider.ts` plus `pi-tools-provider.ts`'s uncited catalog/list surface — thin registry/adapters over already-capsuled kernels; `pi-tools-provider.ts` is cited for its write-slot binding of createPreviewWriteToolDefinition; mcp-provider is dirty-worktree sibling WIP, uncitable at any pin), `guest-types.ts`, and JetBrains extension unless ported directly. Pass 9 residual omissions (all tiny or standing-boundary): `core/pi-tools.ts` (13-line name list, consumed inside tool-ownership + pi-tools-provider capsules), `util.ts` (16L countNewlines/truncateMiddle), `actors/host-event-observer.ts` (32L registration loop over FABRIC_ACTOR_PI_HOST_EVENTS), `activity/types.ts` + `residency/protocol.ts` type-only halves of capsuled seams, and the whole `src/ui/*` plane per the standing boundary. Pass 10 residual omissions: `src/agents/types.ts` type-only transport vocabulary, `src/lifecycle/types.ts`/`src/state/types.ts`/`src/topology/types.ts`/`src/activity/types.ts` pure type modules, `src/audit/index.ts` 27L barrel re-export, and the remaining providers-plane adapters listed above.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`action-registry-invoke-stages.md`](./action-registry-invoke-stages.md)
- [`action-registry-merkle-catalog.md`](./action-registry-merkle-catalog.md)
- [`activity-ledger-bounded-store.md`](./activity-ledger-bounded-store.md)
- [`actor-context-digest.md`](./actor-context-digest.md)
- [`actor-delivery-policy-triad.md`](./actor-delivery-policy-triad.md)
- [`actor-drain-single-flight.md`](./actor-drain-single-flight.md)
- [`actor-global-registry.md`](./actor-global-registry.md)
- [`actor-ownership-ladder.md`](./actor-ownership-ladder.md)
- [`actor-privacy-status-cascade.md`](./actor-privacy-status-cascade.md)
- [`actor-stop-the-world-halt.md`](./actor-stop-the-world-halt.md)
- [`actor-validwhile-sandbox.md`](./actor-validwhile-sandbox.md)
- [`agent-runtime-and-retry.md`](./agent-runtime-and-retry.md)
- [`agent-semaphore-abortable-gate.md`](./agent-semaphore-abortable-gate.md)
- [`agent-thinking-transfer.md`](./agent-thinking-transfer.md)
- [`agent-transport-family.md`](./agent-transport-family.md)
- [`agents-budget-ledger.md`](./agents-budget-ledger.md)
- [`architecture.md`](./architecture.md)
- [`audit-allowlist-projection.md`](./audit-allowlist-projection.md)
- [`audit-persisted-details-budget.md`](./audit-persisted-details-budget.md)
- [`audit-sanitization-ladder.md`](./audit-sanitization-ladder.md)
- [`audit-trace-envelope.md`](./audit-trace-envelope.md)
- [`bench-pier-paired-comparison.md`](./bench-pier-paired-comparison.md)
- [`bounded-progress-preview-pump.md`](./bounded-progress-preview-pump.md)
- [`branch-summary-versioned-envelope.md`](./branch-summary-versioned-envelope.md)
- [`call-time-capability-rejection.md`](./call-time-capability-rejection.md)
- [`certification-rpc-benchmark-gate.md`](./certification-rpc-benchmark-gate.md)
- [`certification-threshold-ladder.md`](./certification-threshold-ladder.md)
- [`child-compact-control-plane.md`](./child-compact-control-plane.md)
- [`compact-intent-single-slot.md`](./compact-intent-single-slot.md)
- [`compaction-bounds.md`](./compaction-bounds.md)
- [`compaction-continuity-cut.md`](./compaction-continuity-cut.md)
- [`compaction-enricher-seam.md`](./compaction-enricher-seam.md)
- [`compaction-normalization-contract.md`](./compaction-normalization-contract.md)
- [`compaction-projection-folds.md`](./compaction-projection-folds.md)
- [`compaction-reconstruction-qa.md`](./compaction-reconstruction-qa.md)
- [`compaction-summary-render.md`](./compaction-summary-render.md)
- [`compaction-typed-instructions.md`](./compaction-typed-instructions.md)
- [`config-migration-ladder.md`](./config-migration-ladder.md)
- [`core-abortable-settlement.md`](./core-abortable-settlement.md)
- [`core-approval-ladder.md`](./core-approval-ladder.md)
- [`core-capability-combustion.md`](./core-capability-combustion.md)
- [`core-evidence-runner.md`](./core-evidence-runner.md)
- [`core-file-ops-hardening.md`](./core-file-ops-hardening.md)
- [`core-tool-capture.md`](./core-tool-capture.md)
- [`core-tool-lifecycle.md`](./core-tool-lifecycle.md)
- [`core-tool-result-proxy.md`](./core-tool-result-proxy.md)
- [`deterministic-continuation-oracle.md`](./deterministic-continuation-oracle.md)
- [`direct-tool-approval-bridge.md`](./direct-tool-approval-bridge.md)
- [`durable-actor-activation-compensation.md`](./durable-actor-activation-compensation.md)
- [`execution-service-host-call-switch.md`](./execution-service-host-call-switch.md)
- [`extension-entry-composition.md`](./extension-entry-composition.md)
- [`fabric-exec-boundary-repairs.md`](./fabric-exec-boundary-repairs.md)
- [`fabric-exec-result-assembly.md`](./fabric-exec-result-assembly.md)
- [`fabric-state-assembly-ladder.md`](./fabric-state-assembly-ladder.md)
- [`git-worktree-lease.md`](./git-worktree-lease.md)
- [`headless-envelope-error-laundering.md`](./headless-envelope-error-laundering.md)
- [`headline-argument-picker.md`](./headline-argument-picker.md)
- [`herdr-socket-client.md`](./herdr-socket-client.md)
- [`host-event-payload-redactor.md`](./host-event-payload-redactor.md)
- [`inbound-control-boundary.md`](./inbound-control-boundary.md)
- [`lexical-complexity-token-fold.md`](./lexical-complexity-token-fold.md)
- [`lifecycle-broker-cursor-subscriptions.md`](./lifecycle-broker-cursor-subscriptions.md)
- [`localterm-pid-liveness.md`](./localterm-pid-liveness.md)
- [`main-agent-identity-delivery.md`](./main-agent-identity-delivery.md)
- [`memory-bounded-regex.md`](./memory-bounded-regex.md)
- [`memory-digest-fold.md`](./memory-digest-fold.md)
- [`memory-discovery.md`](./memory-discovery.md)
- [`memory-lineage.md`](./memory-lineage.md)
- [`memory-search-assembly.md`](./memory-search-assembly.md)
- [`memory-tiered-index.md`](./memory-tiered-index.md)
- [`memory-trace-ingestion.md`](./memory-trace-ingestion.md)
- [`mesh-store.md`](./mesh-store.md)
- [`model-keyed-compaction-thresholds.md`](./model-keyed-compaction-thresholds.md)
- [`nested-agent-skill-rewiring.md`](./nested-agent-skill-rewiring.md)
- [`participant-routing-ladder.md`](./participant-routing-ladder.md)
- [`pi-host-compatibility-gate.md`](./pi-host-compatibility-gate.md)
- [`prewalk-arm-command-surface.md`](./prewalk-arm-command-surface.md)
- [`prewalk-boundary-execution-plane.md`](./prewalk-boundary-execution-plane.md)
- [`prewalk.md`](./prewalk.md)
- [`residency-client.md`](./residency-client.md)
- [`residency-digest-deliveries.md`](./residency-digest-deliveries.md)
- [`resident-host-protocol.md`](./resident-host-protocol.md)
- [`runner-capability-partition.md`](./runner-capability-partition.md)
- [`runtime-functional-type-gate.md`](./runtime-functional-type-gate.md)
- [`runtime-node-process-escape-hatch.md`](./runtime-node-process-escape-hatch.md)
- [`runtime-orchestration-deadline-classifier.md`](./runtime-orchestration-deadline-classifier.md)
- [`runtime-quickjs-guest-kernel.md`](./runtime-quickjs-guest-kernel.md)
- [`state-certificate-binding.md`](./state-certificate-binding.md)
- [`state-transition-two-phase-commit.md`](./state-transition-two-phase-commit.md)
- [`temp-run-root-retention.md`](./temp-run-root-retention.md)
- [`thinking-level-plumbing.md`](./thinking-level-plumbing.md)
- [`tmux-screen-session-twins.md`](./tmux-screen-session-twins.md)
- [`topology-control-plane-exactly-once.md`](./topology-control-plane-exactly-once.md)
- [`topology-participant-directory.md`](./topology-participant-directory.md)
- [`topology-participant-projection.md`](./topology-participant-projection.md)
- [`topology-refresh-lifecycle.md`](./topology-refresh-lifecycle.md)
- [`transport-exit-supervision.md`](./transport-exit-supervision.md)
- [`ux.md`](./ux.md)
- [`veda-headless-runner-contract.md`](./veda-headless-runner-contract.md)
- [`version-pinned-hook-mirror-harness.md`](./version-pinned-hook-mirror-harness.md)
- [`worker-options-contract.md`](./worker-options-contract.md)
- [`worker-run-record-plane.md`](./worker-run-record-plane.md)
- [`write-diff-size-guards.md`](./write-diff-size-guards.md)
- [`write-preview-tool-wrapper.md`](./write-preview-tool-wrapper.md)
