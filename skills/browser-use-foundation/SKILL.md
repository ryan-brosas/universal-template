---
name: browser-use-foundation
description: "Use when building an LLM-driven browser agent: event-bus sessions, watchdog self-healing, DOM serialization to stable indices, schema-enforced action registries with secret redaction, and cache-friendly prompt assembly."
disable-model-invocation: true
---
# Browser Agent Foundation

## Use this for
An LLM-driven browser agent that talks to Chrome over CDP through a typed event bus, self-heals via watchdogs, serializes cross-frame DOM into stable indices, enforces action validity at the schema level with execution-time secret resolution, and assembles prompt-cache-stable per-step messages. Source and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/event-bus-and-profile.md` — ~45 typed result-generic events; BrowserProfile kwargs-splat config compiling+merging Chrome CLI args.
- `references/cdp-session-pool.md` — auto-attach session pool, single validated agent focus (page targets only), ResilientEventBus teardown safety.
- `references/watchdog-pattern.md` — convention-bound handlers (`on_EventName`), CDP circuit breaker with lifecycle exemption, task-canceling cleanup.
- `references/click-download-detection.md` — click coroutine + download wait ladder via direct callbacks (not the event bus); validation-error short-circuit.
- `references/click-element-ladder.md` — scroll→geometry→largest-visible-quad, asymmetric occlusion, per-step timeouts, checkbox verify+JS fallback, re-focus.
- `references/text-input-ladder.md` — clear/focus ladder, React native-setter bypass, char-by-char key grammar, readback + concatenation auto-retry.
- `references/dropdown-option-selection.md` — native select / ARIA menu / combobox / custom dropdown extraction + focus-then-set-with-verify selection.
- `references/security-url-policy.md` — 3-tier URL allow/block with WHATWG-canonicalizing IP classifier (inet_aton + NFKC + percent-decode).
- `references/storage-state-persistence.md` — cookie/localStorage save/load with atomic ladder + session-cookie expires normalization + origin-scoped restore.
- `references/downloads-watchdog.md` — auto-download policy matrix, ingress filename sanitization, local/remote completion split.
- `references/dom-watchdog-state-assembly.md` — parallel DOM+screenshot state with remaining-budget timeout + minimal-recovery fallback.
- `references/local-browser-launch.md` — subprocess launch with temp-dir retry on profile locks + graceful terminate-then-kill teardown.
- `references/har-recording-watchdog.md` — CDP Network → HAR 1.2 with embed/attach content modes + monotonic timing.
- `references/dom-eval-serializer.md` — ultra-concise LLM DOM tree with interactive-only indexing + explicit truncation guards.
- `references/navigation-readiness.md` — lifecycle-event polling with loaderId/timestamp staleness defense, adaptive same-domain timeouts.
- `references/element-actor.md` — geometry fallback chain (getContentQuads→getBoxModel→JS rect), largest-visible-quad selection, real mouse-event sequences.
- `references/cross-frame-visibility.md` — AX trees merged across frames, visibility via reverse ancestor-chain intersection, disjoint llm/eval representations.
- `references/dom-serializer-pipeline.md` — prune → paint-order → collapse → bbox → index-last; shadow DOM always kept; selector_map bridge.
- `references/action-registry.md` — decorator registry compiled to per-page discriminated unions; one action per turn.
- `references/tools-compaction.md` — URL-scoped `<secret>` resolution at execution time, TOTP minting, typed round-trips, single replaceable state message.
- `references/agent-step-loop-phases.md` — phased step() with stale-state clearing point, captcha outcomes as memory, forced-done at max_steps.
- `references/step-error-taxonomy.md` — classify interrupt/transient/terminal/parse errors; never-wedge step counter under timeout cancellation.
- `references/message-compaction.md` — dual-gate rolling summarization, recursive memory blocks, anti-inference framing, secret pre-redaction.
- `references/prompt-assembly.md` — 8-template system-prompt matrix; volatile content segregated to message tail for prompt-cache hits.
- `references/llm-provider-protocol.md` — Protocol-based provider interface, two-mode ainvoke, central strict-schema optimizer.
- `references/token-cost-service.md` — layered pricing resolution, class-separated token costing (cached/uncached/5m/1h writes).
- `references/mcp-bridge.md` — foreign MCP JSON-Schema tools compiled into the native registry (one execution path).
- `references/filesystem-device-auth.md` — in-memory typed files with snapshotting; RFC 8628 device-flow auth.
- `references/action-timeout-hang-guard.md` — env→caller→wait_for timeout ladder turning hung CDP handlers into error-results (nan/inf degrade-to-default).
- `references/browser-error-memory-channel.md` — BrowserError long/short-term memory slots routed into ActionResult; unannotated errors re-raise loudly.
- `references/navigate-empty-dom-recovery.md` — `_root is None` OR empty repr probe, 3s/5s retry ladder, net-error vs CDP-client error classification.
- `references/click-schema-swapping.md` — delete-and-reregister click schema per model capability; tabs-before diff auto-switches to spawned tabs.
- `references/autocomplete-field-handling.md` — four-signal combobox/datalist detection, delay-only-JS-driven rule, actual-value mismatch surfacing.
- `references/upload-containment-ladder.md` — allowlist→downloads→basename-match admission with owned-name rebuild + realpath containment (GHSA-j9hj-92j8-jv9h).
- `references/page-search-find-iife.md` — zero-LLM page grep/find over CDP: JSON-dumps param injection, in-value error returns, true-total pagination.
- `references/extraction-dual-path.md` — try-then-downgrade schema admission, shared 120s/10k overflow contracts, already_collected prompt dedupe.
- `references/markdown-structure-chunking.md` — atomic-block grammar → header-preferred greedy split → persistent table-header overlap; exact char-offset tiling.
- `references/pdf-print-pipeline.md` — printToPDF with explicit-font templates + margins-with-headers rule + `(n)` filename dedupe.
- `references/scroll-viewport-paging.md` — cssVisualViewport measurement, serial awaited page-scrolls with settle gaps, 1000px metric fallback.
- `references/js-auto-repair.md` — six idempotent regex repairs for LLM-mangled JS; exceptionDetails/wasThrown dual detection; images-before-truncation.
- `references/done-action-duality.md` — structured vs free-text completion; mode='json' enum serialization; downloads-only auto-attach.
- `references/sensitive-redaction-ladder.md` — longest-first single-pass alternation redaction (#5135); reverse key-name detection for typed secrets.
- `references/domain-pattern-url-matching.md` — SECURITY-CRITICAL glob matcher: https-default scheme pinning, wildcard refusal matrix, fail-closed errors.
- `references/fire-forget-highlight-tasks.md` — done-callback task wrapper retrieving exceptions on fire-and-forget; fail-open PIL highlight pipeline with negative font caching.
- `references/aboutblank-keepalive.md` — pre-close last-tab seeding, is_cdp_connected-gated recovery, triple-idempotent screensaver injection.
- `references/screenshot-watchdog-contract.md` — target-type validation with page-list fallback; cancel-safe pre-capture highlight removal outside finally.
- `references/permissions-connect-grant.md` — one-shot Browser.grantPermissions on connect event, fail-open error policy.
- `references/cdp-request-timeout-wrapper.md` — send_raw wait_for subclass re-raising plain TimeoutError; inner 60s < outer 180s ordering.
- `references/variable-detection.md` — element-attributes-before-value-patterns classifier with specific-before-general keyword ladder and value dedupe.
- `references/key-code-mapping.md` — Windows VK table with symbol aliases, bare-modifier Left normalization (Right keeps its own code), single-char Key/Digit synthesis.
- `references/mcp-action-bridge.md` — stdio MCP tools → create_model param schemas → registry closures with special-param stripping.
- `references/config-env-rebase-singleton.md` — env-rebase config singleton: live environment property delegation in long-running agent processes.
- `references/rust-sdk-stdio-transport.md` — manual chunk-and-split JSON-RPC framing over asyncio streams, pending-future map with fail-all-on-reader-death, notification queue beside responses.
- `references/terminal-binary-discovery.md` — env→packaged→install-dirs→PATH binary ladder gated by a `--help` capability probe; agent-tools dir trusted only when ripgrep is present.
- `references/sdk-event-history-projection.md` — turn-span slicing, keyed delta-concatenation vs terminal replace, unkeyed positional matching, synthetic dynamic action schema via create_model, injected final `done`.
- `references/session-replay-rollbacks.md` — compaction re-base (`replay_from_seq`) then sequential rollbacks deleting user turns plus `before_seq`-linked context events.
- `references/result-failure-extraction.md` — result precedence done-tool→session marker→streamed fallback; transport-error forgiveness after a final result; structured-output JSON salvage.
- `references/token-usage-reconstruction.md` — sum-vs-max dual fold of model.usage vs token_count snapshots, presence-keyed Anthropic cache-read promotion, pricing that skips snapshots when deltas exist.
- `references/profile-sdk-translation.md` — first-typed-value profile walk → BU_* env + omit-null payload; secrets cross as placeholder names only; sets sorted for determinism.
- `references/direct-cdp-prenavigation.md` — navigate→verify-poll→rewrite-task triad with all-or-nothing fallback to terminal-run execution.
- `references/event-browser-state-reconstruction.md` — recursive URL/tab mining incl. printed dict reprs (json+ast.literal_eval), internal-endpoint filter, last-wins fold, screenshot tail.
- `references/notification-fallback-recovery.md` — richer-source arbitration between response history and live notifications (empty|truncated|longer|result-only), stable cross-channel dedupe, preserve-history-on-cancel.
- `references/laminar-span-reconstruction.md` — never-throws Laminar shim, post-hoc per-turn/tool span replay, base64-placeholder attribute budgeting, local-pricing cost math.
- `references/beta-agent-facade.md` — signature/module identity surgery to mirror the Python Agent, runtime.ping protocol pin, fixed teardown ordering, local `done` semantics over a remote core.
- `references/profile-config-diamond.md` — four-parent Playwright kwargs diamond with AliasChoices back-compat; validators don't run on unset defaults (validate_default unset).
- `references/profile-chrome-arg-compiler.md` — five flag families merged into one CLI list; extract-merge-dedupe keeps exactly ONE --disable-features so disable_security can't break extensions.
- `references/profile-copy-isolation.md` — copy-on-launch profile isolation: transient-file skip set, shutil-triple lock-error detection, original profile read-only forever.
- `references/profile-display-resolution.md` — headless/headful viewport FSM ending in `headless ⇒ no_viewport=False ∧ viewport set`; no-display forces headless.
- `references/profile-crx-extension-cache.md` — download-once CRX cache with Cr24 header recovery, MV3 gate both paths, per-extension degrade-don't-fail, storage prepopulation patch.
- `references/session-manager-pool-refcount.md` — targets vs sessions as separate entities; refcounted removal at zero sessions; create-and-register inside ONE lock.
- `references/session-manager-single-slot-handlers.md` — one global Page.lifecycleEvent handler routed session→target into per-target ring buffers; second registration would freeze all other tabs.
- `references/session-manager-focus-recovery.md` — claim-inside-lock/work-outside-lock recovery with completion-event broadcast, most-recent-tab switch, emergency fallback tab, always-signal finally.
- `references/dom-views-element-hash-triple.md` — element_hash vs compute_stable_hash vs ax_name matching ladder; substring dynamic-class filtering with sorted deterministic output.
- `references/dom-views-scrollability-css-gate.md` — CDP flag → scroll/client rect delta (+1px) → explicit overflow auto|scroll|overlay gate; visible overflow is NOT scrollable; iframes always show hints.
- `references/dom-serializer-paint-order-union.md` — per-document disjoint rect unions processed highest-paint-first; incoming-rect clipping; fail-open 5000-rect cap; transparent layers never occlude.
- `references/dom-serializer-html-noise-rules.md` — shadow-root-first HTML reconstruction; SPA state-blob skip rules (display:none code, bpr-guid ids, base64 imgs); thead synthesis for markdownify.
- `references/dom-serializer-clickable-ladder.md` — veto-before-affirm interactivity ladder: JS-listener flag, label[for] double-activation veto, wrapper depth-2 form controls, AX roles, cursor-pointer fallback.
- `references/actor-page-lazy-session.md` — lazy CDP attach + gather-enable domains; conservative Python-string JS repair; LLM element-by-prompt returns None outside selector_map.
- `references/agent-gif-renderer.md` — placeholder/new-tab frame filtering, latin1→unicode_escape goal-text decoding (CJK), font ladder to load_default, close-every-image finally.
- `references/filesystem-replace-missing-text.md` — `replace_file_str` absent-`old_str` guard (#5498): truthful error WITHOUT rewrite; memory object and disk bytes untouched.
- `references/filesystem-csv-normalization.md` — CsvFile normalize-on-write: csv.reader→writer re-serialization, double-escape detector, combined append re-normalization, blank-append no-op.
- `references/filesystem-filename-sanitize-resolve.md` — basename-first validate→sanitize→re-validate ladder with was_sanitized flag, single resolved-key dict, model-facing correction notes.
- `references/dom-enhanced-snapshot-decoder.md` — CDP DOMSnapshot positional string-table decoding: style-index alignment, DPR bounds division, documented 3,000× list→set clickability fix.
- `references/log-fifo-streaming.md` — non-blocking FIFO log handler: lazy open on first write, drop when no reader, reset on broken pipe; agent/cdp/events pipe trio keyed by session-id suffix.
- `references/llm-responses-serializer.md` — Responses-API input flattening: refusal/tool-call degrade-to-VISIBLE-TEXT placeholders, role-differentiated part filtering.
- `references/sandbox-function-streaming.md` — decorator compiles a local async fn to AST-stripped source + pruned imports + cloudpickle(explicit/self/closure/global params) -> one SSE POST; fail-open callbacks, fatal transport errors, _NO_RESULT sentinel, signature surgery.
- `references/mcp-server-agent-fallback.md` — BrowserUseServer three-ring tool surface: direct CDP tools + session verbs + ONE agent fallback whose failures degrade to strings; empty-list allowed_domains guard (SecurityWatchdog reads [] as unrestricted); Bedrock/OpenAI provider ladder.
- `references/sync-cloud-event-tunnel.md` — CloudSync four-state gate (disabled/authenticated/auth-flow/anonymous-drop), TEMP_USER_ID preservation, batch {events:[...]} POSTs with device_id stamping, 10s timeout, total never-raise handler; device flow persists cloud_auth.json, logout unlinks it.
- `references/agent-judge-verdicts.md` — LLM judge over agent traces: 40k-char per-field budgets, last-10 screenshots, ground-truth HIGHEST-PRIORITY section, auto-false failure list, impossible-task classification, structured JudgementResult attached WITHOUT overriding the self-reported success.
- `references/skills-self-installer.md` — SKILL.md fan-out to 8 assistant dirs via path-builder dict; live harness-CLI text > embedded fallback (silent binary-missing / loud binary-broken); ancestor-chain validation before mkdir; uv tool-install gate.

## Capsule map
- **Transport & events** — `event-bus-and-profile`, `cdp-session-pool`, `watchdog-pattern`, `navigation-readiness`: typed command bus, auto-attach pools, self-healing monitors, readiness signals.
- **Action (watchdog handlers)** — `click-download-detection`, `click-element-ladder`, `text-input-ladder`, `dropdown-option-selection`: robust CDP click/type/select with download wait, React-native-setter, and framework-revert verification.
- **Tools service (action layer)** — `action-timeout-hang-guard`, `browser-error-memory-channel`, `navigate-empty-dom-recovery`, `click-schema-swapping`, `autocomplete-field-handling`, `upload-containment-ladder`, `page-search-find-iife`, `extraction-dual-path`, `pdf-print-pipeline`, `scroll-viewport-paging`, `js-auto-repair`, `done-action-duality`: the whole `tools/service.py` action surface with its timeout/error/containment guards.
- **Security & persistence** — `security-url-policy`, `storage-state-persistence`, `downloads-watchdog`, `sensitive-redaction-ladder`, `domain-pattern-url-matching`: SSRF-hardened URL policy, crash-safe cookie/localStorage, auto-download + filename sanitization, longest-first secret redaction, fail-closed domain gating.
- **Lifecycle & infra** — `local-browser-launch`, `har-recording-watchdog`, `aboutblank-keepalive`, `screenshot-watchdog-contract`, `permissions-connect-grant`, `cdp-request-timeout-wrapper`, `fire-forget-highlight-tasks`, `config-env-rebase-singleton`, `log-fifo-streaming`: subprocess launch/teardown with lock recovery, HAR 1.2 network capture, session keep-alive + capture + permission + timeout hardening, live config singleton, tail-able named-pipe log streaming.
- **Perception** — `cross-frame-visibility`, `dom-serializer-pipeline`, `dom-eval-serializer`, `dom-watchdog-state-assembly`, `markdown-structure-chunking`, `dom-enhanced-snapshot-decoder`: frame-tolerant AX merging, LLM-safe indexed element lists, budget-guarded state assembly, structure-aware page markdown, renderer-free DOMSnapshot geometry/styles.
- **Action** — `element-actor`, `key-code-mapping`, `action-registry`, `tools-compaction`: real input events + VK code table, schema-enforced per-page tools, secret resolution at execution time.
- **Agent loop & ecosystem** — `agent-step-loop-phases`, `step-error-taxonomy`, `message-compaction`, `prompt-assembly`, `llm-provider-protocol`, `token-cost-service`, `variable-detection`, `mcp-action-bridge`, `mcp-bridge`, `filesystem-device-auth`, `llm-responses-serializer`: phased steps with classified recovery, bounded cacheable context, provider-neutral calls, cost tracking, history-derived variables, external tool bridges, scratch state, wire-format content degradation.
- **Agent scratch filesystem** — `filesystem-replace-missing-text`, `filesystem-csv-normalization`, `filesystem-filename-sanitize-resolve`: truthful replace errors, canonical LLM CSV storage, and traversal-safe messy-filename admission — completing the in-memory file-store plane around the device-auth/snapshotting capsule.
- **Rust-core bridge (beta Agent)** — `rust-sdk-stdio-transport`, `terminal-binary-discovery`, `beta-agent-facade`, `profile-sdk-translation`, `direct-cdp-prenavigation`: subprocess JSON-RPC transport with capability-gated binary discovery, drop-in facade identity + protocol pin, config handoff without secret leakage, verified pre-navigation.
- **Event-log projection & recovery** — `sdk-event-history-projection`, `session-replay-rollbacks`, `result-failure-extraction`, `notification-fallback-recovery`, `event-browser-state-reconstruction`, `token-usage-reconstruction`: flat event streams rebuilt into actions/results, undo/compaction folds, success/failure precedence, dual-channel arbitration, browser-state and usage/cost reconstruction.
- **Observability replay** — `laminar-span-reconstruction`: GenAI-convention LLM/tool spans reconstructed post-hoc from events with exporter-safe attribute budgeting.
- **Profile & launch config** — `profile-config-diamond`, `profile-chrome-arg-compiler`, `profile-copy-isolation`, `profile-display-resolution`, `profile-crx-extension-cache`: the whole `browser/profile.py` config plane — kwargs diamond, flag compilation with feature-merge invariant, live-profile copy isolation, viewport FSM, extension provisioning.
- **CDP session lifecycle** — `session-manager-pool-refcount`, `session-manager-single-slot-handlers`, `session-manager-focus-recovery`: the whole `browser/session_manager.py` — event-driven pool sync, single-slot registry workaround, crash-recovering agent focus.
- **DOM identity & geometry** — `dom-views-element-hash-triple`, `dom-views-scrollability-css-gate`, `dom-serializer-paint-order-union`: stable element identity across reloads, honest scrollability, occlusion filtering without a renderer.
- **HTML/markdown support & actors** — `dom-serializer-html-noise-rules`, `dom-serializer-clickable-ladder`, `actor-page-lazy-session`, `agent-gif-renderer`: clean HTML reconstruction, interactivity heuristics, standalone page-handle surface, history GIF rendering.
- **Cloud & eval planes** — `sandbox-function-streaming`, `mcp-server-agent-fallback`, `sync-cloud-event-tunnel`, `agent-judge-verdicts`, `skills-self-installer`: remote function execution over cloudpickle+SSE, agent-as-MCP-server with string-degrading fallback, fail-silent telemetry gating, dual-bookkeeping LLM judging, multi-assistant skill distribution.

## Extending the foundation
Add one references-fileshaped capsule per portable seam: one loader line, one grouped map entry, decisive source with an invariant, a direct-test probe, and a `search_graph` retrieval.
Pass 6 (2026-08-24) method note: filename-granular citation-vs-inventory grep exposed ~26k never-cited production lines despite five prior passes; the biggest wins were whole-file reads of "boring config" (`browser/profile.py`) and "plumbing" (`browser/session_manager.py`) — invariants there (flag-merge, single-slot registries, validator-defaults gap) were undocumented anywhere else.
Pass 7 (2026-08-24) method note: drift re-entry past `3c989dc0` (5 upstream commits) plus a fresh citation-vs-inventory sweep still found 20 never-cited files after six passes; whole-file reads of `filesystem/file_system.py` (943L), `dom/enhanced_snapshot.py`, `logging_config.py` FIFO half, and `llm/openai/responses_serializer.py` yielded 6 capsules — the drift commits themselves contributed only the missing-text guard, proving inventory sweeps outlive drift waves.

## Provenance
Indexed in Codebase Memory as `mnt-hdd-utopia-inspo-agents-browser-use` (`/mnt/hdd/utopia/inspo/agents/browser-use`, canonical root); ~108,966 lines at pin `main@85ddbfe`. STALE-TWIN adopted pass 7 (2026-08-24): the repo moved under `agents/` long ago and the short-name `browser-use` project still serves the pre-drift graph (`/mnt/hdd/utopia/inspo/browser-use`, 6,322n @ `3c989dc`) — refresh-in-place is impossible once the root moved, so every Retrieve block and this section cite the path-slugged twin. Source and its direct tests remain authoritative; the graph is a discovery index, not truth.

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-agents-browser-use` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Live at last verification (2026-08-24, post-drift pull to `85ddbfe`): root `/mnt/hdd/utopia/inspo/agents/browser-use`, branch `main@85ddbfe`, 6,316 nodes / 35,402 edges, status ready; parse_partial limited to Dockerfile + bin/lint.sh (neither cited by any capsule); gitignored outputs/assets excluded by design. Source and direct tests decide shipped claims.
Pass 8 revalidation (2026-08-25): assignment pin moved this lane to the SHORT-NAME project `browser-use`, now refreshed past the stale twin: root `/mnt/hdd/utopia/inspo/browser-use`, branch main @ `85ddbfe` (full sha 85ddbfedf609166b2d2c76c3d80506649fee82a9), 6,322 nodes / 35,320 edges, status ready, parse_partial only Dockerfile + bin/lint.sh, skipped=0 — verified equal to the repo HEAD before citing. All pass-8 Retrieves run against this short-name project; earlier capsules remain pinned to their own retrieval projects.

## Boundaries
Adopt the event bus, session pooling, watchdogs, serialization pipeline, registry contracts, error taxonomy, compaction, and prompt layout; adapt CDP transport, cloud bindings, and product-specific messaging unless a target requires them. The beta `browser_use/beta/service.py` plane is the Python↔Rust bridge: adopt its transport framing, event-log projection folds, dual-channel recovery, and facade identity techniques; adapt the browser-use-terminal RPC vocabulary (`agent.run_task`, `runtime.ping`), BU_* env names, Laminar vendor attributes, and cloud profile/proxy fields; omit the Rust core's own internals (separate binary) and product nudge messaging.
Pass 6 additions: the profile/session-manager/DOM-support planes are portable as a unit; adapt Chrome flag tables (live vendor behavior that rotates), extension IDs, CJK font names, and the LinkedIn-specific bpr-guid skip rule to your targets. Omitted-with-reason at this pin: `mcp/server.py` (1,294L product MCP server), `browser/demo_mode.py` (922L side-panel UI), `agent/views.py` (1,003L declarative schemas around mined contracts), llm provider twins (standing ruling), `sandbox/sandbox.py` + `agent/judge.py` (conditional targets, no porting question yet).
Pass 7 additions: adopt the filesystem scratch-store trio and DOMSnapshot decoder as units; adapt pipe naming, style-request lists, and placeholder wording. Omitted-with-reason at this pin: `agent/cloud_events.py` (284L cloud-sync event schemas — product transport, user_id/device_id server-filled contract noted for a future cloud-porting question), `browser/video_recorder.py` (141L imageio macro-block padding — thin optional-dep wrapper), `llm/aws/chat_bedrock.py` + `chat_anthropic.py` (~550L boto3 credential ladder — standing llm-provider-twin ruling), `mcp/cli_mcp.py` + `mcp/__main__.py` (CLI-3.0 MCP wrapper — product surface like mcp/server.py), `init_cmd.py` (448L GitHub template scaffolder — UX flow), `actor/playground/*` (demo scripts), `logging_config.py` setup half beyond FIFOHandler (product console formatting).
Pass 8 additions (2026-08-25): resolved the pass-6 conditional targets — `mcp/server.py` is mined for its tool-surface architecture (`mcp-server-agent-fallback`; adopt the rings + string-degrading failures, adapt provider ladder), `sandbox/sandbox.py` for the remote-execution compiler (`sandbox-function-streaming`), `agent/judge.py` for the eval loop (`agent-judge-verdicts`). New units: `sync/service.py`+`auth.py` tunnel gating (`sync-cloud-event-tunnel`) and `skills/install.py` distribution (`skills-self-installer`). Still omitted-with-reason: `browser/cloud/cloud.py` + `agent/cloud_events.py` (cloud task/event schemas await a real cloud-porting question), `mcp/cli_mcp.py`+`__main__.py` (product CLI wrapper), `init_cmd.py`, playgrounds.
