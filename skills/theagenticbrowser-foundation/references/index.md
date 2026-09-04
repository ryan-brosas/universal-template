<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# TheAgenticBrowser: Browser-Agent Foundation

## Use this for
Build or port an LLM-driven web-navigation agent on Playwright: give the model stable per-element ids by bridging injected `mmid` attributes into accessibility-tree snapshots, minimize those trees to interactive-only surfaces without orphaning children, detect side-effect UI after every action through a page-side MutationObserver bridge, degrade clicks to JavaScript execution with select-option/same-tab/menu special cases, run a Planner→Browser→Critique loop where the critique LLM owns termination and infrastructure errors never crash the run, scrub megabyte DOM payloads out of critique inputs at both prompt and history layers, replay multi-agent runs as ONE valid OpenAI-format conversation via pseudo-tool synthesis, verify actions with opt-in pre/post screenshot VLM diffing, expose runs over SSE with disconnect-safe teardown, and survive stage failures through a catch-and-notify retry funnel whose only exits are critique-owned termination or context-death; (pass 3) port the page-side user-overlay interaction plane itself — two-axis collapsed/expanded × init/processing/done state that survives navigation via Python mirroring + full replay, an expose_function bridge surface, escaping ladders for evaluate-injected messages, type-gated display filters, scroll choreography, and a verified defect ledger to fix at port time. Source code is ground truth; references carry decisive excerpts and graph retrieval. The repo ships NO test suite — every capsule records a coverage caveat and pins deterministic graph/source evidence instead.

## Load the matching source dump
- `./mmid-aria-reconciler.md` — aria-keyshortcuts side-channel injection + snapshot reconciliation for stable element targeting.
- `./dom-prune-unravel.md` — post-order tree pruning with child-lifting unravel and semantic interactivity filters.
- `./mutation-observer-feedback.md` — subscribe/act/drain window that rewrites success strings into "fetch new DOM" guidance.
- `./sse-task-api.md` — per-task orchestrator registry, notification-queue bridge, SSE stream with disconnect-safe finally-cleanup.
- `./clear-before-type-entry.md` — unconditional value-blank before keyboard fill; silent property-set fork and its no-event caveat.
- `./js-click-ladder.md` — attach-wait → scroll → JS click with option/link/menu special cases and error-as-data returns.
- `./browser-manager-fallback.md` — Steel CDP → local persistent-context → temp-dir recovery ladder; adopt-don't-create remote contexts.
- `./planner-browser-critique-loop.md` — three-tier error taxonomy (browser=data, planner/critique=fatal, context-length=graceful exit).
- `./dom-scrub-for-critique.md` — dual-layer placeholder filtering of DOM tool responses (prompt string + typed history rebuild).
- `./unified-transcript-synthesis.md` — pseudo-tool-call synthesis for planner/critique/screenshot turns + prefix-diff append storage.
- `./screenshot-diff-verification.md` — opt-in pre/post capture, intent-carrying VLM diff, search-no-change special case.
- `./dual-model-client-config.md` — prefixed env families for text vs vision models; sync/async client split.
- `./google-search-tool.md` — API search as one-action tool: num≤10 clamp, error-string returns, open_url chaining contract.
- `./composite-enter-click.md` — fill+submit compound skill: Enter-on-same-selector rule, success-prefix gate between halves.
- `./pdf-extraction-tool.md` — httpx download → pdfplumber parse → unconditional finally-cleanup.
- `./url-navigation-contract.md` — protocol normalization at every boundary; navigation timeout as soft success.
- `./per-run-evidence-folder.md` — import-time monotonic task_N folder collecting all debug artifacts.
- `./overlay-reinjection.md` — Python-owned UI state re-injected and fully replayed on every domcontentloaded.
- `./step-failure-retry-funnel.md` — outer catch-and-continue funnel: per-iteration error-slot resets, the stale-`browser_response` carry trap, no iteration cap anywhere.
- `./final-response-subagent.md` — critique-owned `final_response` tool_plain delegating to a dedicated answer-extraction LLM call that bans success-stub answers.
- `./page-selection-selfheal.md` — closed-page-filtered last-tab selection; null-handle context re-creation with one recursion; two-branch launch-failure ladder.
- `./overlay-visibility-text-extraction.md` — single-evaluate overlay-hide → innerText + prefixed alt-text collect → visibility revert for clean LLM page text.
- `./notification-message-protocol.md` — type-keyed prefixes, last-moment JS escaping of message AND enum value, detail-gated display, best-effort evaluate.
- `./highlight-screenshot-bracket.md` — fail-open pulsating-border highlight with self-removing animation class; None-returning start/end screenshot brackets.
- `./error-envelope-taxonomy.md` — five-class exception family carrying user-facing message + original_error; BrowserNavigationError/CritiqueError are dead twins.
- `./import-time-logging-bootstrap.md` — import-time root-logger configuration, handler-idempotent reconfiguration, shared-handler hijack of openai/autogen loggers.
- `./async-cli-question-channel.md` — executor-offloaded stdin question channel (dead code at this pin; reference pattern for headless ports).
- `./dead-format-conversion-twins.md` — uncalled pydantic-ai→OpenAI dict converter vs live pseudo-tool synthesis; ConversationVerifier offline transcript grader.
- `./overlay-state-machine.md` — two-axis collapsed/expanded × init/processing/done state with class-carried DOM re-derivation on view switches (pass 3).
- `./overlay-bridge-contract.md` — the four expose_function bridges + three page entry points, context-scoped registration, and silent-failure census (pass 3).
- `./message-injection-escaping.md` — pre-quoted f-string composition with json.dumps-at-replay vs quote+`<br>`-at-live escaping and the innerHTML sink hazard (pass 3).
- `./navigation-reinjection-replay.md` — domcontentloaded re-injection order, single-flight replay latch, swallow-only-detached policy (pass 3).
- `./type-gated-display.md` — three-site visibility gating for the show-details toggle and its shipped live-vs-replay divergence (pass 3).
- `./chat-scroll-choreography.md` — per-append pin + 5×1s reflow burst + sticky-bottom poll; the predicate that preserves manual scroll-up (pass 3).
- `./question-answer-modal.md` — asyncio.Event handshake over the user_response bridge; complete but caller-dead at this pin (pass 3).
- `./overlay-defects-ledger.md` — five verified latent defects (inverted flag :83, ghost evaluate :240, swallowed state pushes :119-120, innerHTML sink, uncleared interval) as a port-time fix/keep checklist (pass 3).
- `./dom-readiness-error-projection.md` — uncited-until-pass-4 dom_helper.py: silent-expiry readyState poll gating every DOM read + 15-attribute opening-tag projection as failed-action error context (pass 4).
- `./key-combination-twin-ladder.md` — '+' grammar → down/press/up modifier ladder; observer-wrapped tool twin vs bool+screenshot composite twin (pass 4).
- `./bounded-page-identity-read.md` — geturl's 250-char bounded URL+title string, bare-except title fallback, and the exception-laundering quirk to fix at port (pass 4).
- `./ba-tool-registration-grammar.md` — 9×tool_plain + exactly one RunContext tool (`get_dom_fields` via deps_type); docstring-as-schema and the shipped prompt↔schema divergence (pass 4).
- `./api-app-factory-boot-plane.md` — FastAPI app factory, unused API_PREFIX, dead subprocess streamer, insecure CORS pair, and the Dockerfile-vs-__main__ boot truth (pass 4).
- `./orchestrator-bootstrap-token-ledger.md` — per-lane cumulative token ledger fed from result._usage, two-phase async_init with google.com default, input_mode browser fork, import-time logfire scrubbing=False side effect (pass 4).

## Capsule map
- **DOM representation** — `mmid-aria-reconciler`: inject sequential ids via a rarely-used ARIA attribute so the snapshot can be reconciled 1:1 against live DOM nodes; ephemeral, re-injected every capture.
- **DOM representation** — `dom-prune-unravel`: shrink the reconciled tree to interactive elements; unravel wrappers by lifting children; manual index arithmetic is load-bearing.
- **Action feedback** — `mutation-observer-feedback`, `sse-task-api`: page-side MutationObserver → exposed bridge → Python pub-sub with 100 ms drain before unsubscribe and overlay self-exclusion; HTTP side: registry+queue+SSE-finally orchestration for backgrounded tasks.
- **Action tools** — `clear-before-type-entry`, `js-click-ladder`, `composite-enter-click`, `pdf-extraction-tool`, `google-search-tool`, `url-navigation-contract`: one reusable contract each — errors are data, success messages are protocols, timeouts are soft failures.
- **Browser lifecycle** — `browser-manager-fallback`: singleton manager with CDP-first bring-up, corrupt-profile recovery, last-non-closed-page selection.
- **Agent loop** — `planner-browser-critique-loop`: per-agent histories, LLM-owned termination via structured `{feedback, terminate, final_response}`, string-matched context-death handling.
- **Context budget** — `dom-scrub-for-critique`: placeholder elision at two layers keeps the critic cheap AND the browser's next turn valid.
- **Observability & config** — `unified-transcript-synthesis`, `screenshot-diff-verification`, `per-run-evidence-folder`, `overlay-reinjection`, `dual-model-client-config`: one transcript format, visual ground truth, per-run evidence home, nav-proof UI, two-model env config.
- **Loop failure semantics** (pass 2) — `step-failure-retry-funnel`, `error-envelope-taxonomy`: one outer catch-and-continue converts every stage failure into notify+retry; typed exceptions are user-facing envelopes (message + original_error), never control-flow discriminators; two of five classes are dead vocabulary.
- **Answer production** (pass 2) — `final-response-subagent`: termination and answer extraction are decoupled; the critique LLM owns a `final_response` tool that re-reads plan/browser-response through a second model call with success-stub phrasing banned.
- **Browser resilience plane** (pass 2) — `page-selection-selfheal`, `highlight-screenshot-bracket`, `notification-message-protocol`, `overlay-visibility-text-extraction`: closed-filtered last-tab page selection with context self-heal; fail-open decoration and None-returning evidence screenshots; type-keyed/escaped/gated overlay messaging; single-evaluate hide→collect→revert text extraction.
- **Support utilities** (pass 2) — `import-time-logging-bootstrap`, `async-cli-question-channel`, `dead-format-conversion-twins`: import-time idempotent logging bootstrap hijacking openai/autogen loggers; executor-offloaded CLI question channel (dead at this pin); the converter-vs-synthesis duality plus an offline ConversationVerifier grader.
- **Overlay UI plane** (pass 3) — `overlay-state-machine`, `overlay-bridge-contract`, `navigation-reinjection-replay`, `message-injection-escaping`, `type-gated-display`, `chat-scroll-choreography`, `question-answer-modal`, `overlay-defects-ledger`: Python-mirrored two-axis state restored on every navigation with single-flight full-history replay; a four-bridge expose_function surface whose gaps fail silently; two-layer escaping into pre-quoted evaluate f-strings; type-keyed visibility gates that deliberately diverge between live push and replay; three-layer scroll choreography with a sticky-bottom predicate; an asyncio.Event question handshake (caller-dead at this pin); and a five-item verified defect ledger (inverted flag, ghost evaluate, swallowed state pushes, innerHTML sink, timer leak) to fix or keep consciously at port time.
- **Readiness & keyboard primitives** (pass 4) — `dom-readiness-error-projection`, `key-combination-twin-ladder`: the silent-expiry readiness gate under every DOM read plus allowlisted opening-tag projection for failed-action self-correction; the '+' modifier grammar with observer-wrapped success-string protocol and its bool-returning composite twin.
- **Identity, registry & boot planes** (pass 4) — `bounded-page-identity-read`, `ba-tool-registration-grammar`, `api-app-factory-boot-plane`, `orchestrator-bootstrap-token-ledger`: bounded URL+title identity read; the 9+1 tool_plain/RunContext registration split with docstring-as-schema and a shipped prompt↔schema drift; FastAPI factory with dead prefix/subprocess/boot remnants; per-lane token ledger + two-phase init + import-time telemetry side effect.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Re-run the mechanical citation-vs-inventory sweep first (grep every reference citation against the file inventory) — it finds what target lists miss.

## Provenance
TheAgenticBrowser (TheAgentic Community License 1.0 — source-available; SaaS-competing-use restricted), `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory project `mnt-hdd-utopia-inspo-TheAgenticBrowser` (529 nodes / 1699 edges, ready status, indexed at HEAD; only `.env.example` parse-partial + one PNG excluded by design). Pass 2 (2026-08-24): same pin re-entry (head==base==`71daa28`, zero drift); 18→28 capsule-v2 via whole-file citation-vs-inventory sweep over all 36 tracked sources; root `/mnt/hdd/utopia/inspo/TheAgenticBrowser` is a LIVE SYMLINK into `agents/TheAgenticBrowser` (readlink-verified — serves real bytes; no twin adoption needed). Pass 3 (2026-08-24, agents-dir census lane): armed standing target #2 at the SAME zero-drift pin (fetch-first behind=0) — the injectOverlay.js 941L interaction plane + `ui_manager.py`/`js_helper.py`/bridge wiring mined whole-file into 8 more capsule-v2 (28→36); retrieval plane re-verified live rank-1 line-exact ×12 queries; adversarial wrong-project probe (`showExpandedOverlay tawebagent-overlay` on agents-cuga-agent) returns unrelated overlay symbols only. Pass 4 (2026-08-26, dedicated deep-learning lane miner-TheAgenticBrowser): SAME zero-drift pin re-verified live (head==base==`71daa285d655...`, checkout HEAD match, clean tree); work record CREATED at `inspo/TheAgenticBrowser-work/`; citation-vs-inventory sweep over all 40 files vs 36 refs found dom_helper.py fully uncited plus 5 partial planes → 6 new capsule-v2 (36→42) + sse-task-api line-pin correction (~11-line drift recorded at pass 1 under the identical commit — corrected from direct whole-file read); coverage check on all 7 cited paths no_recorded_issue @ gen 2026-08-23T00:02:33Z; six live retrieves line-exact; probe battery caught and fixed 4 imprecise anchors pre-delivery.

## Full view (memory graph)
Revalidate `mnt-hdd-utopia-inspo-TheAgenticBrowser` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Recorded at squeeze time (pass 1): root `/mnt/hdd/utopia/inspo/TheAgenticBrowser` (worktree canonical `/mnt/hdd/utopia/inspo/agents/TheAgenticBrowser`), branch main, HEAD == base == `71daa28`, ready, 14 labels (Function 107 / Method 104 / Package 119), 19 edge types (DEFINES 739, CALLS 333, USAGE 140, WRITES 53, SEMANTICALLY_RELATED 19), entry point `core/main.py:main`; `search_graph --semantic-query '["mmid attribute injection accessibility tree"]'` ranks five PlaywrightManager lifecycle methods top-8; `trace_path Orchestrator.run outbound depth2` = exactly 50 callees; `trace_path do_get_accessibility_info inbound` = 3 callers. Pass 2 re-verified gate 1 live: index_status ready, head==base==`71daa285d655...`, parse_partial only `.env.example`; pass-2 capsules were seam-selected by whole-file source reads with graph Retrieve blocks pinned per capsule (`step_error continue retry`, `get_current_page browser context closed new_page`, `notify_user addSystemMessage escape_js_message`, etc.). Source and direct tests decide shipped claims — here there ARE no tests, so probes cite graph traces and line-pinned source only.

## Boundaries
Adopt pure contracts: mmid bridging, prune/unravel, mutation-feedback rewrite rules, critique-input scrubbing, pseudo-tool transcript synthesis, degradation ladders, error-as-data tool returns; (pass 2) the step-failure funnel + per-iteration slot resets, termination/answer decoupling via a critique-owned sub-call, closed-filtered last-tab selection with null-handle self-heal, single-evaluate overlay-hide text extraction, type-keyed message protocol with last-moment JS escaping, fail-open decoration, import-time idempotent logging bootstrap; (pass 3) two-axis overlay state with DOM re-derivation, the expose_function surface checklist, re-injection + single-flight replay order, pre-quoted evaluate escaping layers, sticky-bottom scroll predicate; (pass 4) silent-expiry readiness gating before DOM reads + allowlisted opening-tag projection as failed-action error context, the '+' modifier down/press/up ladder with observer-wrapped success protocol and its bool-returning composite twin, bounded page-identity reads with graceful title degradation, the 9×tool_plain + one RunContext tool registration split with docstring-as-schema, per-lane cumulative token ledgers fed from each agent result, two-phase async_init owning browser bring-up + start-page navigation. Adapt host-specific integration: Steel Dev endpoint, Google Custom Search keys, overlay UI id/styles, logfire telemetry, IST-timezone helpers; add a hard iteration ceiling/backoff before production use of the retry funnel; replace the innerHTML sink with textContent and unify the live-vs-replay display filters when porting the overlay plane. Omit product surface: the injectOverlay.js visual chrome (styles/SVGs/disclaimer copy — port the interaction CONTRACTS via the pass-3 capsules instead), GUI input mode wiring, video recording, Dockerfile/deployment, README marketing copy; omit as dead code at this pin: `cli_helper.py`, `convert_openai.py` (+ standalone `open_ai_verfication_script.py` — reference-only grader), `prompt_user`/`command_completed` activation paths (complete patterns, zero callers). Known upstream quirks NOT to copy: `show_overlay` inverted flag (`ui_manager.py:83`), ghost `commandExecutionCompleted()` evaluate (`ui_manager.py:240`), blanket debug-swallow in `update_processing_state` (`:119-120`), uncleared 100ms scroll interval per expansion (`injectOverlay.js:578`), duplicated MessageType enums (`message_type.py` vs `ui_messagetype.py`), blocking `requests` inside async google_search, uncalled `get_dom_with_accessibility_info` wrapper, stale-`browser_response` carry into critique prompts after browser-stage raises (`orchestrator.py:532` vs reset slots `:400-401`), missing `bypass_csp=True` on the temp-profile relaunch path (`browser_manager.py:246` vs `:219`), dead exception classes BrowserNavigationError/CritiqueError, substring `"confirm"` Verify-gate false positives, unused loop variable `i` (`orchestrator.py:309`); (pass 4) geturl launders EVERY failure into 'No active page found' (`get_url.py:38-39`) and its `PlaywrightManager(browser_type=…, headless=…)` call-site args are dead vocabulary on the singleton (`get_url.py:19`, same pattern `get_dom_with_content_type.py:42/:74`), import-time class-level `logfire.configure(scrubbing=False)` telemetry side effect (`orchestrator.py:171`), BA_SYS_PROMPT teaches a phantom `get_dom_fields` prompt argument the registered schema does not accept (`browser_agent.py:50` vs `:270-272`), CORS `allow_origins=["*"]` paired with `allow_credentials=True` (`api_routes.py:58-64`), broken `"main:app"` uvicorn target in `__main__` while Dockerfile boots `core.server.api_routes:app` on port 8000 vs module default 8080 (`api_routes.py:187`, `Dockerfile:12`), defined-but-unused `API_PREFIX`, zero-caller `stream_subprocess_output`, stray `print(raw_data)` debug in the fields path (`get_dom_with_content_type.py:87`).

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`api-app-factory-boot-plane.md`](./api-app-factory-boot-plane.md)
- [`async-cli-question-channel.md`](./async-cli-question-channel.md)
- [`ba-tool-registration-grammar.md`](./ba-tool-registration-grammar.md)
- [`bounded-page-identity-read.md`](./bounded-page-identity-read.md)
- [`browser-manager-fallback.md`](./browser-manager-fallback.md)
- [`chat-scroll-choreography.md`](./chat-scroll-choreography.md)
- [`clear-before-type-entry.md`](./clear-before-type-entry.md)
- [`composite-enter-click.md`](./composite-enter-click.md)
- [`dead-format-conversion-twins.md`](./dead-format-conversion-twins.md)
- [`dom-prune-unravel.md`](./dom-prune-unravel.md)
- [`dom-readiness-error-projection.md`](./dom-readiness-error-projection.md)
- [`dom-scrub-for-critique.md`](./dom-scrub-for-critique.md)
- [`dual-model-client-config.md`](./dual-model-client-config.md)
- [`error-envelope-taxonomy.md`](./error-envelope-taxonomy.md)
- [`final-response-subagent.md`](./final-response-subagent.md)
- [`google-search-tool.md`](./google-search-tool.md)
- [`highlight-screenshot-bracket.md`](./highlight-screenshot-bracket.md)
- [`import-time-logging-bootstrap.md`](./import-time-logging-bootstrap.md)
- [`js-click-ladder.md`](./js-click-ladder.md)
- [`key-combination-twin-ladder.md`](./key-combination-twin-ladder.md)
- [`message-injection-escaping.md`](./message-injection-escaping.md)
- [`mmid-aria-reconciler.md`](./mmid-aria-reconciler.md)
- [`mutation-observer-feedback.md`](./mutation-observer-feedback.md)
- [`navigation-reinjection-replay.md`](./navigation-reinjection-replay.md)
- [`notification-message-protocol.md`](./notification-message-protocol.md)
- [`orchestrator-bootstrap-token-ledger.md`](./orchestrator-bootstrap-token-ledger.md)
- [`overlay-bridge-contract.md`](./overlay-bridge-contract.md)
- [`overlay-defects-ledger.md`](./overlay-defects-ledger.md)
- [`overlay-reinjection.md`](./overlay-reinjection.md)
- [`overlay-state-machine.md`](./overlay-state-machine.md)
- [`overlay-visibility-text-extraction.md`](./overlay-visibility-text-extraction.md)
- [`page-selection-selfheal.md`](./page-selection-selfheal.md)
- [`pdf-extraction-tool.md`](./pdf-extraction-tool.md)
- [`per-run-evidence-folder.md`](./per-run-evidence-folder.md)
- [`planner-browser-critique-loop.md`](./planner-browser-critique-loop.md)
- [`question-answer-modal.md`](./question-answer-modal.md)
- [`screenshot-diff-verification.md`](./screenshot-diff-verification.md)
- [`sse-task-api.md`](./sse-task-api.md)
- [`step-failure-retry-funnel.md`](./step-failure-retry-funnel.md)
- [`type-gated-display.md`](./type-gated-display.md)
- [`unified-transcript-synthesis.md`](./unified-transcript-synthesis.md)
- [`url-navigation-contract.md`](./url-navigation-contract.md)
