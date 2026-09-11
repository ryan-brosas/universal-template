<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Pydantic AI Harness Foundation

## Use this for
A pydantic-ai agent harness: capability/toolset abstractions, context-window compaction (sliding-window, anchored incremental summarization, tiered escalation, zero-cost clamp/clear/dedup kit, near-limit warnings, typed failure-gated strategy fallback chains), anchored provider-usage budget estimation with reserved-limit nested summarizer runs, compaction receipts, conversation-history BM25 recall with snapshot recovery, fail-closed scoping, and once-per-instance default-migration warnings, spend budgets, planning stores, guardrail verdict contracts with checksum-validated redaction detectors scanned across content-part text spans, durable step persistence with interrupted-resume classification, scope-qualified memory injection, agent-skills package loading, subagent model menus, tool-output size bands and spill-with-read-back reduction over a hardened overflow store with pageable serialized spills, browser-use delegation with scheme-safe allowlists plus a real Playwright Chromium capability (egress policy with resolve-first private-address blocking, credential redaction, countdown deadlines, cross-frame waits) and You.com search/research capabilities, recoverable-error filesystem tools with path-leak sanitization and FIFO-safe conflict writes, env-denylisted shell execution, Modal/LocalStack sandbox lifecycle, runtime-authored capabilities, and code-execution REPL driving. Source and tests are authoritative; the capsules carry decisive excerpts and derived flows.

## Load the matching source dump
- `./window-resolution.md` — fractions-over-constants context-window resolution with a named fallback ladder.
- `./sliding-window-compaction.md` — pair-safe cutoffs, pin survival, self-reserving receipts.
- `./summarizing-compaction-anchor-update.md` — summarizing compaction anchor update: rolling summary anchor advancement.
- `./summarizer-instructions-field.md` — summarizer instructions field: the nested summary request's system-prompt surface as an overridable field (#669).
- `./tiered-compaction-escalation.md` — tiered compaction escalation: progressive multi-stage context reduction.
- `./zero-cost-compaction-kit.md` — zero-cost compaction kit: deterministic truncation and tool output stripping without LLM roundtrips.
- `./warn-near-limits-strip-inject.md` — warn near limits strip inject: proactive context warnings and system prompt injection.
- `./spend-budget-keys.md` — budget-as-keys, TTL table, validation-against-failure-mode.
- `./spend-gate.md` — the local per-response money gate that stops a runaway loop.
- `./plan-store.md` — six-method async CRUD with a loud event-emission asymmetry.
- `./browser-use-delegation.md` — one `browse_web` tool, session scoping, shielded teardown, factory seam.
- `./tool-output-bands.md` — ordered (over, action) size bands with a `then` fallback.
- `./subagents-menu.md` — named model menu, per-delegate restrictions, always-propagate errors.
- `./capability-store.md` — disk-backed runtime-authored capabilities, atomic manifest, no-`Any` boundary.
- `./monty-exec.md` — synchronous-snapshot REPL driver with three execution modes.
- `./guardrail-verdict-contract.md` — five-action verdict vocabulary (allow/block/replace/retry/approve), threading chains, read-only guard input, approval round trip, failure screening that keeps exception type.
- `./secret-pii-redaction-detectors.md` — ordered checksum-validated secret/PII patterns, validators-bound-to-builtins-not-names, non-re-emitting placeholder functions.
- `./step-persistence-resume-points.md` — settled-boundary snapshots + interrupted-state classification, live-history reference stash for error rescue, (run_id, tool_call_id) effect ledger.
- `./memory-strip-then-inject.md` — scope-qualified marker strip-then-inject, budget-first rendering with visible truncation flags, degrade-don't-die injection errors.
- `./skill-loader-contract.md` — string-typed unique-key YAML frontmatter, name-directory parity, behavioral fields acknowledged-but-reported-inactive.
- `./sandbox-session-lifecycle.md` — shielded-bounded create + checkpointed teardown of owned sandboxes, independent cleanup deadlines that never mask body exceptions, terminal-vs-retryable error classes.
- `./conversation-search-bm25-dual-rendering.md` — dependency-free BM25 recall over persisted history with a dual index/display rendering (rank untruncated, show capped) and ordinal/binary poisoning guards.
- `./conversation-search-snapshot-source.md` — snapshot-union recovery of pre-compaction originals via content-hash suffix/prefix reconciliation; byte-exact summary-artifact exclusion.
- `./conversation-search-scope-tenancy.md` — fail-closed conversation scoping for shared history stores: unlabelled runs search nothing, foreign run ids answer identically to unknown ones.
- `./context-estimator-anchor.md` — anchored context estimation: provider-reported usage as ground truth for the prefix, character heuristic only for the post-anchor tail, changed-instructions rule, compaction-reclaim correction.
- `./compaction-receipts.md` — deterministic secondhand-memory receipt markers appended at compaction boundaries, metadata-keyed de-accumulation, capability-protocol transcript-handle discovery, OTel span events.
- `./request-model-resolution.md` — resolve every per-request policy against the request's model (not the run-start model); trigger validation ladder; realtime-model type guard; no-op compactions emit nothing.
- `./tool-output-spill-readback.md` — production-time spill of oversized tool returns behind ordered size bands with lossless read-back tools, per-call/per-retry handle keys, bounded literal-pattern slicing.
- `./overflow-store-hardening.md` — shared-by-design spill root secured by segment sanitization plus resolved containment (0700), daemon-thread TTL pruning that warns instead of failing the run.
- `./tool-output-payload-kit.md` — payload triage preamble: binary detection, ANSI stripping, chars-vs-tokens measurement aligned with the budget estimator, annotated truncation, JSON shape sketches.
- `./fallback-compaction-chains.md` — FallbackCompaction strategy chains: typed failure-gated fallback with fresh-input replay and last-error re-raise.
- `./reserved-nested-usage-limits.md` — reserved usage limits: nested summarizer runs give back one finite request so they cannot spend the parent's approved request.
- `./default-change-deprecation-channel.md` — scope default migration: tri-state option, once-per-instance HarnessDeprecationWarning naming restore-and-keep spellings, scope-conditional instructions.
- `./guardrail-text-span-scanning.md` — text-span guardrail scanning: per-part then joined-originals passes catch secrets split across content parts; boundary-preserving CachePoint merge.
- `./fs-recoverable-error-ladder.md` — filesystem recoverable-error ladder: subclass whitelist + explicit errno table decide ModelRetry vs run-aborting failure.
- `./fs-path-leak-sanitization.md` — path-leak sanitization + TOCTTOU ordering: realpath before pattern checks, sentinel redaction of host paths from every model-visible message.
- `./fs-fifo-safe-conflict-write.md` — FIFO-hardened optimistic-concurrency writes: classify the descriptor before any byte moves; O_NONBLOCK/O_NOFOLLOW/no-O_TRUNC discipline.
- `./shell-env-credential-denylist.md` — opt-in glob denylist strips provider credentials from child environments; identity-sentinel allow/deny interlock; honest not-a-boundary wording.
- `./playwright-capability-shell.md` — PlaywrightBrowser capability shell: lazy launch, per-run isolation, construction-time durable-execution refusal, install-hint recovery.
- `./playwright-egress-policy.md` — browser egress policy: IDNA-exact matching, resolve-first fail-closed private-address block, kind-split allowlist, two-layer enforcement.
- `./playwright-operation-funnel.md` — browser operation funnel: countdown deadlines across stages, mark-and-count event attribution to spans, chokepoint credential redaction.
- `./playwright-frames-waits.md` — cross-frame reads and waits: aria-ref handles reach iframes; appearing races per-frame while disappearing gathers everywhere.
- `./youdotcom-recoverable-search.md` — You.com capabilities: status-classified retries, sources as ToolReturn metadata, freshness validated at construction.
- `./toll-pageable-spill-serializer.md` — pageable spill serializers: indented_json/json_lines presets escape Unicode line separators so read-back offsets stay on the grid.
- `./browser-use-allowlist-normalization.md` — browser-use allowlist normalization: strictly-narrowing scheme qualification keeps file:// off any allowlist; shielded session teardown.
- `./code-mode-limit-markers.md` — CodeMode sandbox-limit markers: table-driven exhaustion classification enforced complete by an exhaust-every-declared-option test.
- `./monty-dispatch-refusal-delivery.md` — host-side dispatch refusals are delivered as call-site exceptions inside the sandbox, never as feed aborts.
- `./temporal-resource-limit-stripping.md` — Temporal-aware resource limits: strip elapsed-time caps under replay determinism, keep memory caps.
- `./dynamic-workflow-resource-limits.md` — live workflow sandbox limits: strict-key validation at construction, merge-onto-backstop resolve, await-exempt duration cap.
- `./logfire-managed-prompt-baggage-envelope.md` — managed-prompt resolution once per run as an outermost baggage envelope that never contaminates the resolution span.
- `./acp-turn-commit-discipline.md` — ACP turn commit discipline: commit-only-on-finish, four-exit-path tool-call closeout, late-cancel-during-persist answers cancelled with committed usage.
- `./acp-approval-scope-ladder.md` — ACP approval scope ladder: canonical-JSON scope keys for "always" decisions, per-session memory, pending-not-running denies, external-execution refusal.
- `./acp-bounded-stream-serialization.md` — ACP bounded stream serialization: escaped-byte-length chunking under a 64 KiB reader buffer, base64/fallback coercion, truncation markers for atomic payloads.
- `./acp-session-store-contract.md` — ACP session store contract: save fails soft / load fails loud, purpose-built error shapes, pop-then-cancel takeover before restore.
- `./acp-editor-native-toolsets.md` — ACP editor-native toolsets: capability-gated fs/terminal routing through the client connection, cwd rooting, cancellation-safe terminal kill/release.
- `./acp-model-config-routing.md` — ACP model config routing: stable config-option surface, advertised-id validation, per-run model override that never mutates the shared agent.
- `./acp-prompt-content-blocks.md` — how do editor-supplied multimodal prompt blocks become model user-content without downgrading inline data.
- `./acp-stop-reason-usage-plane.md` — how does a turn's response encode which exit path fired.
- `./acp-tool-call-presentation.md` — how do you render rich editor tool-call cards (kind/locations/diff) without lying about unrecognized tools.

## Capsule map
- **Compaction** — `window-resolution.md`, `sliding-window-compaction.md`, `summarizing-compaction-anchor-update.md`, `tiered-compaction-escalation.md`, `zero-cost-compaction-kit.md`, `warn-near-limits-strip-inject.md`, `context-estimator-anchor.md`, `compaction-receipts.md`, `request-model-resolution.md`, `summarizer-instructions-field.md`: resolve a real window per model; trim with pair-safe cutoffs, pin survival, self-reserving receipts, rolling summary anchors, tiered compaction escalation, zero-cost compaction kit, near-limit injection, and a separately overridable system-instruction surface for the nested summarizer agent; anchor budget estimates on provider usage; mark boundaries with deterministic receipts; resolve policies against the request's model.
- **Compaction strategies** — `fallback-compaction-chains.md`, `reserved-nested-usage-limits.md`: typed failure-gated strategy fallback with fresh-input replay; nested summarizer runs reserve one parent request.
- **Recall** — `conversation-search-bm25-dual-rendering.md`, `conversation-search-snapshot-source.md`, `conversation-search-scope-tenancy.md`, `default-change-deprecation-channel.md`: BM25 recall over persisted history (rank untruncated, show capped); recover pre-compaction originals from snapshot stores; fail-closed conversation scoping; once-per-instance default-migration warnings.
- **Guardrails** — `guardrail-verdict-contract.md`, `secret-pii-redaction-detectors.md`, `guardrail-text-span-scanning.md`: one five-action verdict vocabulary across input/output/tool edges; ordered checksum-validated redaction detectors that never re-emit what they remove; joined-span scanning that catches secrets split across content parts.
- **Durability** — `step-persistence-resume-points.md`: append-only events, complete-vs-interrupted snapshot states, tool-effect ledger for replay-safety decisions.
- **Retrieval capabilities** — `memory-strip-then-inject.md`, `skill-loader-contract.md`: scope-qualified idempotent memory injection; fail-loud string-typed skill-package loading.
- **Sandboxing** — `sandbox-session-lifecycle.md`: owned/attached remote sessions with shielded-bounded create, checkpointed teardown, and terminal-vs-retryable error classes.
- **Spend** — `spend-budget-keys.md`, `spend-gate.md`: budget-as-keys with no reset jobs; a local per-response money gate.
- **Planning** — `plan-store.md`: six-method protocol, loud event asymmetry, duplicate-id rejection.
- **Delegation & tools** — `browser-use-delegation.md`, `subagents-menu.md`, `tool-output-bands.md`, `tool-output-spill-readback.md`, `overflow-store-hardening.md`, `tool-output-payload-kit.md`, `toll-pageable-spill-serializer.md`, `code-mode-limit-markers.md`: browser-use agent delegation, named model menus, size-band tool-return management, spill-with-read-back reduction of oversized returns over hardened shared storage with pageable serialized layouts, marker-table sandbox-exhaustion classification.
- **Browser & egress** — `playwright-capability-shell.md`, `playwright-egress-policy.md`, `playwright-operation-funnel.md`, `playwright-frames-waits.md`, `browser-use-allowlist-normalization.md`: a real stateful Chromium behind lazy-launch/per-run isolation with durability refused at construction; IDNA-exact resolve-first egress policy; deadline/redaction/attribution funnel; cross-frame read-and-wait duality; scheme-safe allowlist normalization.
- **Web research** — `youdotcom-recoverable-search.md`: status-classified retries and structured source metadata over the You.com APIs.
- **Tool hardening** — `fs-recoverable-error-ladder.md`, `fs-path-leak-sanitization.md`, `fs-fifo-safe-conflict-write.md`, `shell-env-credential-denylist.md`: model-correctable-vs-fatal error classification, resolve-before-authorize path hygiene, descriptor-classified conflict writes, opt-in environment credential stripping.
- **Runtime authoring & execution** — `capability-store.md`, `monty-exec.md`, `monty-dispatch-refusal-delivery.md`, `dynamic-workflow-resource-limits.md`: disk-backed capability persistence; Monty REPL driving; refusal-as-call-site-exception delivery across the snapshot boundary; workflow sandbox limits strict-key-validated at construction and merged onto backstops with await-exempt duration.
- **Determinism & telemetry** — `temporal-resource-limit-stripping.md`, `logfire-managed-prompt-baggage-envelope.md`: replay-safe resource limits (timing stripped, memory kept); resolve-once baggage envelopes for remotely-managed prompts.
- **Editor protocol (ACP)** — `acp-turn-commit-discipline.md`, `acp-approval-scope-ladder.md`, `acp-bounded-stream-serialization.md`, `acp-session-store-contract.md`, `acp-editor-native-toolsets.md`, `acp-model-config-routing.md`: expose a pydantic-ai agent to editors over the Agent Client Protocol — turn-granular commit/rollback with best-effort closeout on every exit path; scoped approval memory keyed by canonical JSON; wire-size-bounded streaming and truncation markers over stdio JSON; an asymmetric save-fails-soft/load-fails-loud session store with atomic live-session takeover; capability-gated editor-native fs/terminal toolsets with cancellation-safe terminal cleanup; stable-surface model switching resolved per-run against a never-mutated shared agent.
- **ACP prompt content blocks** — `acp-prompt-content-blocks`: how do editor-supplied multimodal prompt blocks become model user-content without downgrading inline data.
- **ACP stop-reason / usage plane** — `acp-stop-reason-usage-plane`: how does a turn's response encode which exit path fired.
- **ACP tool-call presentation** — `acp-tool-call-presentation`: how do you render rich editor tool-call cards (kind/locations/diff) without lying about unrecognized tools.
## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pydantic-ai-harness (MIT), current pin `main@76db3dec` — pass 7 (2026-08-26, dedicated lane miner-pydantic-ai-harness): records reconciliation pass (leaf already carried 50 refs while the ledger row sat at pass 0 and no work record existed; an unrecorded post-pass-6 wave had re-indexed this head and mined #669 into summarizer-instructions-field.md without landing any records); created inspo/pydantic-ai-harness-work/{state,research,verification}.md, repaired the dead `frameworks/` checkout path + dead slugged graph-project citation in that capsule, and mined six uncited `experimental/acp` capsule-v2 seams (acp-turn-commit-discipline, acp-approval-scope-ladder, acp-bounded-stream-serialization, acp-session-store-contract, acp-editor-native-toolsets, acp-model-config-routing) wired under a new Editor protocol (ACP) map group → 56 capsule-v2 refs; Codebase Memory project `pydantic-ai-harness` (9,546 nodes / 51,434 edges, ready, full mode, head==base `76db3dec`, 0 parse_partial; coverage checked no_recorded_issue on all cited ACP paths @ gen 2026-08-24T14:03:49Z). Earlier history at pin `main@f971198`: pass 4 drift re-entry: upstream advanced 15 commits past `c79fabc5` — PlaywrightBrowser, YouSearch/YouResearch, spill serializer presets, FallbackCompaction, filesystem/shell/guardrail/browser-use hardening). Pass-4 history: a sibling session authored the 16-capsule drift wave and wired it into this leaf but died before any records landed; the reactive-drift lane ([DONE:234]) gate-3-verified all 16 against source at the new head, then mined the three uncovered seams (logfire-managed-prompt-baggage-envelope, monty-dispatch-refusal-delivery, temporal-resource-limit-stripping) → 48 capsule-v2. Codebase Memory project `pydantic-ai-harness` (9,543 nodes / 51,349 edges, ready, full mode, head==base `f971198c`, 0 parse_partial; slugged twin project `mnt-hdd-utopia-inspo-frameworks-pydantic-ai-harness` serves the identical new head — both refreshed post-drift, no stuck-twin). Passes 1–3 were mined at pin `c79fabc5` (8,375 nodes / 44,554 edges). Source and its tests remain authoritative; the graph is a discovery index, not truth. Pass 6 (2026-08-24, dedicated lane, zero-drift closure-hold converted into a GATE-5 RUNNER UPGRADE — the passes 1–4 "runner BLOCKED" caveat is RETIRED): upstream tests executed for the first time at this pin inside a fresh uv venv (`uv venv /tmp/harness-p6-venv --python 3.12`; `uv pip install -e . pytest pytest-asyncio dirty-equals inline_snapshot opentelemetry-sdk pyyaml sniffio pytest-examples 'logfire[variables]'` then DOWNGRADES to lockfile pins `pydantic-monty==0.0.19` + `logfire==4.33.0`, which are load-bearing: monty 0.0.21 drifts memory-limit message thresholds and logfire 4.41 drifts managed-variable span attribute shapes vs the snapshot-pinned suites); full suite **3,404 passed / 36 skipped / 0 failed** excluding only external-service planes (tests/media, tests/planning/test_postgres.py, tests/planning/test_redis.py, tests/modal_sandbox, tests/coder) plus a `-W ignore::pytest.PytestRemovedIn10Warning` collection shim; capsule-bearing suites spend/code_mode/compaction/filesystem/guardrails alone = **1,210 passed**. Pass 7 (2026-08-24, dedicated lane drain-lane-pydantic-ai-frameworks, DRIFT RE-ENTRY): upstream advanced exactly one commit `f971198c`→`main@76db3dec` (#669: expose the summarizer agent's `instructions` on `SummarizingCompaction`, default = prior hardcoded string, kw-only field preserving constructor compat) → +1 capsule-v2 `summarizer-instructions-field.md` (48→49) with its two new direct tests EXECUTED GREEN 2/2 in the pass-6 venv. METADATA-ONLY RE-INDEX TRAP fired and was adjudicated per skill protocol: after the pull, BOTH graph projects reported head==base==`76db3dec` while still serving PRE-drift content (`_DEFAULT_INSTRUCTIONS` name_pattern-absent; short-name node/edge counts identical to the old `f971198c` generation) — refresh-in-place WAS possible (repo never moved/symlinked) and both `pydantic-ai-harness` (9,546n/51,434e) and slugged twin `mnt-hdd-utopia-inspo-frameworks-pydantic-ai-harness` (9,546n/51,122e) were re-indexed by path and content-verified serving the new symbol BEFORE any capsule citation was written. Sibling capsule `summarizing-compaction-anchor-update.md` re-pinned whole-file at the new head (every symbol range ≥:89 shifted +13/+15 lines; Probe/Retrieve blocks upgraded to ts-form with live-resolved evidence); two stale sibling one-line cites repaired (`reserved-nested-usage-limits` `_summarizing_compaction.py:629`→`:641`; `compaction-receipts` consumer `:443`→`:457`). Coverage no_recorded_issue+metadata_match ×2 cited paths; adversarial retrieval unchanged. Pass 8 (2026-08-24, dedicated lane drain-lane-pydantic-ai-frameworks): zero upstream drift (origin-fetched behind=0) → closure-hold converted by POSING standing conditional #2 porting question (dynamic-workflow resource limits) — the `dynamic_workflow/` subsystem had ZERO prior capsules; read `dynamic_workflow/_toolset.py` (793L) resource-limits plane + all five direct tests; authored NEW `dynamic-workflow-resource-limits.md`: strict-key validation (`_RESOURCE_LIMIT_KEYS = frozenset(WorkflowResourceLimits.__annotations__)`; total=False TypedDict validates nothing at runtime so a typo'd `max_durations_secs` would silently disable the CPU-runaway cap), three-way resolve (None→backstop `{max_memory:256MiB}`, `'unlimited'`→{} TOTAL opt-out, partial→merge ONTO backstop), construction-time validation in `__post_init__`, await-exempt duration semantics (Monty counts per bytecode step; sub-agent latency incl. concurrent gather never accrues; NO default cap), + relation ruling vs replay twin `temporal-resource-limit-stripping.md` (same field name, opposite concerns). +1 capsule-v2 (49→50) wired into Runtime authoring & execution group. GATE-5 REAL RUNNER: full `tests/dynamic_workflow/` suite GREEN **107 passed** at pin `76db3dec` in standing `/tmp/harness-p6-venv`. Coverage no_recorded_issue ×2 cited paths generation_matches=true; graph rank#1 line-exact (`_resolve_resource_limits` :93-108; also surfaces the `code_mode/_toolset.py:239-258` same-name twin for future passes).

## Full view (memory graph)
Revalidate `pydantic-ai-harness` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure contracts: window-resolution, pair-safe compaction, anchored incremental summaries, tiered escalation accounting, typed strategy-fallback chains, the clamp/clear/dedup kit, strip-then-inject warnings and memory blocks, budget-as-keys, the spend gate, the PlanStore protocol, size bands, the model menu, the capability store, the Monty executor, the guardrail verdict vocabulary, redaction detectors including joined-span scanning, resume-point persistence, the skill-loader contract, sandbox lifecycle discipline, anchored usage-based context estimation, deterministic compaction receipts, dual-rendering BM25 recall with snapshot-union recovery and fail-closed scoping, once-per-instance default-change warnings, spill-with-read-back tool-output reduction over a sanitized shared store with line-grid-preserving serializers, request-model policy resolution, the two-surface summarizer prompt split (a `{messages}` user-turn template plus a separately overridable static system-instruction field whose default preserves legacy behavior byte-for-byte), reserved-request nested runs, recoverable-error ladders, resolve-before-authorize path handling, FIFO-safe conflict writes, env denylisting, the egress policy ladder, the operation funnel's redaction chokepoint, cross-frame waits, status-classified API retries, marker-table exhaustion mapping, refusal-as-data delivery across sandbox boundaries, replay-safe resource limits, resolve-once managed-prompt baggage envelopes, and the ACP editor-protocol contracts (turn-granular commit with four-exit-path tool-call closeout, canonical-JSON approval scopes, escaped-byte-length stream bounding with truncation markers, save-fails-soft/load-fails-loud session stores with takeover-before-restore, capability-gated editor-native toolsets, stable-surface per-session model routing). Adapt the pydantic-ai runtime/LLM, the storage backends (SQLite/Postgres/Redis/Mongo), and the vendor SDKs (Playwright, browser-use, youdotcom) whose phrasings are load-bearing. Omit the host-specific CLI productization, browser-use version pinning, DNS-rebinding closure (upstream tracks it proxy-side), and per-tenant worker wiring unless ported directly.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`acp-approval-scope-ladder.md`](./acp-approval-scope-ladder.md)
- [`acp-bounded-stream-serialization.md`](./acp-bounded-stream-serialization.md)
- [`acp-editor-native-toolsets.md`](./acp-editor-native-toolsets.md)
- [`acp-model-config-routing.md`](./acp-model-config-routing.md)
- [`acp-prompt-content-blocks.md`](./acp-prompt-content-blocks.md)
- [`acp-session-store-contract.md`](./acp-session-store-contract.md)
- [`acp-stop-reason-usage-plane.md`](./acp-stop-reason-usage-plane.md)
- [`acp-tool-call-presentation.md`](./acp-tool-call-presentation.md)
- [`acp-turn-commit-discipline.md`](./acp-turn-commit-discipline.md)
- [`browser-use-allowlist-normalization.md`](./browser-use-allowlist-normalization.md)
- [`browser-use-delegation.md`](./browser-use-delegation.md)
- [`capability-store.md`](./capability-store.md)
- [`code-mode-limit-markers.md`](./code-mode-limit-markers.md)
- [`compaction-receipts.md`](./compaction-receipts.md)
- [`context-estimator-anchor.md`](./context-estimator-anchor.md)
- [`conversation-search-bm25-dual-rendering.md`](./conversation-search-bm25-dual-rendering.md)
- [`conversation-search-scope-tenancy.md`](./conversation-search-scope-tenancy.md)
- [`conversation-search-snapshot-source.md`](./conversation-search-snapshot-source.md)
- [`default-change-deprecation-channel.md`](./default-change-deprecation-channel.md)
- [`dynamic-workflow-resource-limits.md`](./dynamic-workflow-resource-limits.md)
- [`fallback-compaction-chains.md`](./fallback-compaction-chains.md)
- [`fs-fifo-safe-conflict-write.md`](./fs-fifo-safe-conflict-write.md)
- [`fs-path-leak-sanitization.md`](./fs-path-leak-sanitization.md)
- [`fs-recoverable-error-ladder.md`](./fs-recoverable-error-ladder.md)
- [`guardrail-text-span-scanning.md`](./guardrail-text-span-scanning.md)
- [`guardrail-verdict-contract.md`](./guardrail-verdict-contract.md)
- [`logfire-managed-prompt-baggage-envelope.md`](./logfire-managed-prompt-baggage-envelope.md)
- [`memory-strip-then-inject.md`](./memory-strip-then-inject.md)
- [`monty-dispatch-refusal-delivery.md`](./monty-dispatch-refusal-delivery.md)
- [`monty-exec.md`](./monty-exec.md)
- [`overflow-store-hardening.md`](./overflow-store-hardening.md)
- [`plan-store.md`](./plan-store.md)
- [`playwright-capability-shell.md`](./playwright-capability-shell.md)
- [`playwright-egress-policy.md`](./playwright-egress-policy.md)
- [`playwright-frames-waits.md`](./playwright-frames-waits.md)
- [`playwright-operation-funnel.md`](./playwright-operation-funnel.md)
- [`request-model-resolution.md`](./request-model-resolution.md)
- [`reserved-nested-usage-limits.md`](./reserved-nested-usage-limits.md)
- [`sandbox-session-lifecycle.md`](./sandbox-session-lifecycle.md)
- [`secret-pii-redaction-detectors.md`](./secret-pii-redaction-detectors.md)
- [`shell-env-credential-denylist.md`](./shell-env-credential-denylist.md)
- [`skill-loader-contract.md`](./skill-loader-contract.md)
- [`sliding-window-compaction.md`](./sliding-window-compaction.md)
- [`spend-budget-keys.md`](./spend-budget-keys.md)
- [`spend-gate.md`](./spend-gate.md)
- [`step-persistence-resume-points.md`](./step-persistence-resume-points.md)
- [`subagents-menu.md`](./subagents-menu.md)
- [`summarizer-instructions-field.md`](./summarizer-instructions-field.md)
- [`summarizing-compaction-anchor-update.md`](./summarizing-compaction-anchor-update.md)
- [`temporal-resource-limit-stripping.md`](./temporal-resource-limit-stripping.md)
- [`tiered-compaction-escalation.md`](./tiered-compaction-escalation.md)
- [`toll-pageable-spill-serializer.md`](./toll-pageable-spill-serializer.md)
- [`tool-output-bands.md`](./tool-output-bands.md)
- [`tool-output-payload-kit.md`](./tool-output-payload-kit.md)
- [`tool-output-spill-readback.md`](./tool-output-spill-readback.md)
- [`warn-near-limits-strip-inject.md`](./warn-near-limits-strip-inject.md)
- [`window-resolution.md`](./window-resolution.md)
- [`youdotcom-recoverable-search.md`](./youdotcom-recoverable-search.md)
- [`zero-cost-compaction-kit.md`](./zero-cost-compaction-kit.md)
