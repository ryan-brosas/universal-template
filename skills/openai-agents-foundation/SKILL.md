---
name: openai-agents-foundation
description: "Use when building multi-agent frameworks: guardrail tripwires running parallel to generation, typed handoffs with history filtering, serializable human-in-the-loop run state, and the turn-resolution ladder that turns model output into action."
disable-model-invocation: true
---
# OpenAI Agents Foundation

## Use this for
A multi-agent framework: guardrail tripwires racing generation, typed handoffs with a session/model history split, the resolution ladder that turns model output into action, parallel tool dispatch with failure arbitration, and serializable human-in-the-loop run state. Source and tests are the contract; references resolve to decisive excerpts, ladders, and state contracts.

## Load the matching source dump
- `references/guardrail-tripwires.md` — tripwire-as-exception halting, parallel-by-default input guardrails.
- `references/typed-handoffs.md` — typed delegation, session/model input split, redaction-aware errors.
- `references/resolution-ladder.md` — one exhaustive dispatch pass then a fixed priority chain to action.
- `references/handoff-arbitration.md` — single-winner arbitration with honest losers and faithful history.
- `references/parallel-tool-arbiter.md` — isolation-default-on batches, failure arbitration, order-faithful re-sort.
- `references/malformed-input-grading.md` — consumer-graded handling (raise/degrade/fail-closed/redact).
- `references/versioned-snapshot-contract.md` — stamp-every-write schema contract with loud unknown-version refusal.
- `references/approval-ledger.md` — scope AND precision approvals with the human's rejection text attached.
- `references/parking-resume.md` — detached snapshots, canonical-identity re-binding, ambiguity fails loud.
- `references/hardened-deserialization.md` — exact-type validation, redaction-by-default, trusted-message allowlist.
- `references/conservative-context-serialization.md` — capability-tier serialization with machine-readable gap metadata.
- `references/run-loop-turn-orchestration.md` — turn spine ordering, hook pairs, occurrence-key stream dedup.
- `references/streaming-persistence-gates.md` — when streamed output reaches the store; tripwire vs error asymmetry.
- `references/blocked-output-retention-rules.md` — side-effect items survive a rejected final turn; reasoning tying.
- `references/redacted-persistence-group-sanitizer.md` — payload-free ExceptionGroup rebuild for failed persistence.
- `references/streamed-save-variant-routing.md` — which save callback each next-step outcome uses; count travel.
- `references/max-turns-handler-finalization.md` — handler output validated/guardrailed/persisted before recording.
- `references/sandbox-vs-guardrail-ordering.md` — sequential guardrails fire before sandbox resource creation.
- `references/pending-input-admission-split.md` — client commits immediately; server waits for acceptance evidence.
- `references/session-persisted-count-ledger.md` — per-turn persisted-count slicing plus missing-tool-output rescue.
- `references/session-rewind-protocol.md` — verify-then-pop exact suffix with restore-on-failure; stray sweep.
- `references/session-input-callback-reconciliation.md` — identity-then-frequency classification of callback outputs.
- `references/server-conversation-delta-tracker.md` — three-view dedupe (identity/server-ids/fingerprints); rewind-before-replay + re-mark-after-success delta cycle.
- `references/conversation-item-sanitization.md` — required-ID allowlist vs strip rules for conversation-backed stores.
- `references/model-retry-veto-trio.md` — absolute vetoes and three approval lanes over replay safety.
- `references/conversation-locked-compat-retries.md` — legacy retry path beside a policy engine; provider-retry disable matrix.
- `references/tool-invocation-dedup-gate.md` — same-id/different-content fails loud; exact replays dedupe silent.
- `references/tool-execution-plan-approvals.md` — plan buckets plus approved/rejected/pending resolution order.
- `references/hosted-mcp-approval-callbacks.md` — mark-executed-before-run exactly-once callback execution.
- `references/tool-identity-collision-resolution.md` — bare/namespaced/deferred lookup keys; last-winner collision ladder.
- `references/strict-json-schema-conversion.md` — value-preserving strict conversion under a node budget.
- `references/session-protocol-wrapper-optin.md` — signature-introspected context injection for legacy sessions.
- `references/sqlite-session-cancel-tolerant-writes.md` — cancellation absorbed until outcome known; connection quarantine.
- `references/session-limit-resolution.md` — explicit→configured→unlimited limit ladder; 0 vs None distinction.
- `references/stream-event-item-mapping.md` — closed RunItem→event-name mapping; approvals/compaction stay silent.
- `references/replay-created-by-sanitizer.md` — one-funnel strip of output-only fields (created_by etc., incl. nested shell chunks) before replay.
- `references/approval-item-identity.md` — approvals hash by object identity; derived accessors never join the identity; to_input_item raises.
- `references/latest-wins-dedupe-anchors.md` — two-pass dedupe keeping latest payload at earliest anchor slot for causal pairs.
- `references/orphan-call-pruning.md` — drop calls without outputs + reasoning cascade + program-ownership + pending-shell/tool-search exceptions.
- `references/compaction-mode-resolution.md` — previous_response_id vs input ladder with unstored-response memory under auto.
- `references/compaction-replace-rollback.md` — lock-guarded clear→add transaction; restore drains to settlement even under repeated cancellation.
- `references/compaction-output-normalization.md` — post-compact orphaned-assistant-id strip (whole-list decision) + content-shape repair.
- `references/serialized-approval-ownership-relink.md` — schema-1.17 ownership window + all-or-nothing fail-open identity relink after deserialize.
- `references/max-turns-guardrail-race.md` — one-shot max-turns latch so a tripped input guardrail can win the terminal-error slot.
- `references/guardrail-blocked-message-customization.md` — safe-metadata formatter with total fallback; synchronous-only redaction boundary.
- `references/mcp-manager-server-hygiene.md` — ingress identity-dedupe, derived active set, finally-refresh cleanup lifecycle.
- `references/mcp-error-content-precedence.md` — isError results keep content blocks over structuredContent; JSON-in-text fallback for unknown blocks.
- `references/weakref-agent-backrefs.md` — lazy weakref agent reads with release_agent nulling strong slots, sentinel-guarded resolution.
- `references/multi-provider-prefix-routing.md` — first-slash prefix routing ladder; explicit map precedence, alias/model_id openai + unknown modes, best-effort aclose.
- `references/provider-retry-advice-ladder.md` — adapter-side retry classification: unsafe markers → x-should-retry header authority → chain-walked network/timeout → transient statuses → retry-after-only.
- `references/run-error-handler-recovery.md` — kind-keyed handlers turn terminal errors into schema-validated final outputs; four result shapes, strict dict keys.
- `references/agent-tool-result-cache.md` — nested agent-as-tool results cached by identity with scope-qualified signature fallback; ambiguity fails closed; weakref GC cleanup.
- `references/tool-failure-schema-bypass.md` — three-state failure formatter config; cancellation Exception coercion; SDK-generated error strings bypass structured output schemas.
- `references/chatcmpl-stream-output-layout.md` — lazily memoized stream output_index slots; message-slot reservation shifts later calls +1; unknown index fails loud.
- `references/chatcmpl-assistant-turn-assembly.md` — items→messages single-slot assistant state machine; flush rules; signed-reasoning never crosses turns.
- `references/chatcmpl-tool-output-text-coercion.md` — empty/non-text tool outputs: keep-text → warn+placeholder → strict UserError ladder with all-content opt-in.
- `references/provider-reasoning-round-trip.md` — duck-typed reasoning-field precedence on emit; origin-gated DeepSeek replay policy as injectable hook.
- `references/chatcmpl-param-gating-headers.md` — store/include_usage default ON only for api.openai.com else omitted; ContextVar header override merged last across all adapters.
- `references/websocket-session-pinned-runconfig.md` — frozen session pins one RunConfig+MultiProvider; identity alignment per call; run_config override fails loud.
- `references/hook-error-precedence-gather-cancel.md` — gather-with-cancel drains siblings on first child failure; hook pairs run concurrently; hook error beats sibling cancellation.
- `references/turn-resolution-hook-pairing.md` — run-level ∥ agent-level end/handoff pairs in one gather-with-cancel; on_agent_end exactly once per run; handoff output committed before hooks.
- `references/usage-ledger-aggregation.md` — null-guarded Usage.add, strict per-request entry synthesis rule, fail-soft raw-usage sidecars.
- `references/usage-serialize-roundtrip.md` — legacy list wire shape kept on write; read tolerates list/dict + missing fields, corrupt snapshots degrade to zeros.
- `references/tool-output-trimmer-window.md` — user-message sliding window; copy-never-mutate; validate-before-preview; smaller-than-original gate.
- `references/handoff-history-summary-nesting.md` — ordered summary|verbatim interleave with provenance digests; nested summaries re-flatten before re-summarizing.
- `references/handoff-history-parser-tail.md` — numbered-record transcript parse ladder: multi-line records, JSON-first, bare-role recovery, prose rejected not fabricated.
- `references/tool-not-found-message-ladder.md` — raise-vs-return-to-model miss branch; fail-soft formatter (exception/None/non-string → default); mark-executed-before-user-code; one output item on live and resume paths.
- `references/final-output-from-tools.md` — closed tool_use_behavior ladder (never/first/named/custom-callable); bare+qualified name match; tool-decided finals share the model-decided pipeline.
- `references/conversation-tracker-hydration.md` — source-aware resume seeding per dedupe view; last-id-bearing response chain; unsent local outputs stay sendable; one-shot guard.
- `references/nested-history-ownership-rebase.md` — filter→reconcile→rebase ownership protocol; normalized digests; identity/occurrence deques; ambiguity fails closed.
- `references/adapter-escape-hatch-kwargs.md` — fixed-precedence extra_query/metadata/extra_body/extra_args merge with copies; promote-and-pop reasoning_effort; precondition-gated settings.
- `references/usage-span-projection.md` — span-type-dispatched usage attachment with delta snapshots, zero-guard, finally-block teardown; adapter-owned model spans.
- `references/resume-approval-reconciliation.md` — snapshot→coerce→validate→reconcile resume ladder; malformed approvals fail closed; nested-state transfer/drop/reject rules.
- `references/anyllm-provider-plane.md` — capability-gated API selection, two-key provider cache with retry-disable clone, hostile-payload normalization into SDK types.
- `references/anyllm-transport-sanitize-close.md` — private-API transport-kwargs escape, subtractive replay sanitization, shield-and-detach stream close under cancellation.
- `references/resume-collector-lanes.md` — one generic approval collector with injected per-type extractors/builders/checkers; output-exists idempotence; rejection and re-interruption exactly once.
- `references/anyllm-chat-path.md` — chat-completions adapter assembly: requests-count-without-usage, content-filter refusal promotion, span-before-yield streaming, one-tool-call-per-assistant-message history repair.
- `references/run-lifecycle-span-lifecycle.md` — task/turn/agent/handoff span creation, pairing, error attachment, and finish-on-every-exit with snapshot-delta usage.
- `references/ledger-reconciliation-protocol.md` — durable-ledger missed-pass recovery: verify disk truth, compose outside the shared file, scoped own-row edit, read-back.
- `references/nonstreamed-turn-twin.md` — non-streamed run_single_turn mirrors the streamed skeleton; on_llm_end deferred past processing via defer_llm_end_hooks.
- `references/streamed-terminal-usage-folding.md` — terminal-response assembly with empty-output rescue; failed retry attempts folded as prepended zero-entries on both paths.
- `references/anyllm-chat-request-construction.md` — chat payload assembly order: effort-gated thinking, provider-conditional repair, per-provider header routing, promote-and-pop, logprobs defer.
- `references/computer-shell-execution-lanes.md` — bucket→filter→plan→execute→commit for computer/local-shell: serial execution, safety-check acknowledgment, position-ordered incremental commits.

## Capsule map
- **Guardrails & handoffs** — `guardrail-tripwires`, `typed-handoffs`, `handoff-history-summary-nesting`, `handoff-history-parser-tail`, `nested-history-ownership-rebase`: tripwire halting, typed delegation, session/model split, summary-nested handoff input, round-trippable summary transcript parsing, mutation-proof forwarded-item ownership.
- **Turn engine** — `resolution-ladder`, `handoff-arbitration`, `parallel-tool-arbiter`, `malformed-input-grading`, `tool-not-found-message-ladder`, `final-output-from-tools`: model output → action, arbitration, failure handling, missing-tool feedback ladder, tool-decided final outputs.
- **Run state & HITL** — `versioned-snapshot-contract`, `approval-ledger`, `parking-resume`, `hardened-deserialization`, `conservative-context-serialization`: serializable, resumable, hardened run persistence.
- **Turn loop & streaming** — `run-loop-turn-orchestration`, `streaming-persistence-gates`, `streamed-save-variant-routing`, `blocked-output-retention-rules`, `redacted-persistence-group-sanitizer`, `max-turns-handler-finalization`, `sandbox-vs-guardrail-ordering`, `stream-event-item-mapping`, `hook-error-precedence-gather-cancel`, `turn-resolution-hook-pairing`, `nonstreamed-turn-twin`, `streamed-terminal-usage-folding`.
- **Session persistence** — `pending-input-admission-split`, `session-persisted-count-ledger`, `session-rewind-protocol`, `session-input-callback-reconciliation`, `conversation-item-sanitization`, `server-conversation-delta-tracker`, `conversation-tracker-hydration`.
- **Model retry** — `model-retry-veto-trio`, `conversation-locked-compat-retries`.
- **Tools & approvals planning** — `tool-invocation-dedup-gate`, `tool-execution-plan-approvals`, `hosted-mcp-approval-callbacks`, `tool-identity-collision-resolution`, `strict-json-schema-conversion`.
- **Session stores & protocol** — `session-protocol-wrapper-optin`, `sqlite-session-cancel-tolerant-writes`, `session-limit-resolution`.
- **Items & identity** — `replay-created-by-sanitizer`, `approval-item-identity`, `weakref-agent-backrefs`: replay funnel, per-occurrence approvals, released backrefs.
- **Input normalization & dedupe** — `latest-wins-dedupe-anchors`, `orphan-call-pruning`: causal-order-preserving dedupe, orphan cascade.
- **Compaction & resume** — `compaction-mode-resolution`, `compaction-replace-rollback`, `compaction-output-normalization`, `serialized-approval-ownership-relink`: responses.compact modes/rollback/replay shapes, schema-1.17 identity relink.
- **Streaming errors & redaction** — `max-turns-guardrail-race`, `guardrail-blocked-message-customization`: terminal-error latch, customizable placeholder with total fallback.
- **MCP integration hygiene** — `mcp-manager-server-hygiene`, `mcp-error-content-precedence`: deduped lifecycle manager, isError-over-structured policy.
- **Model providers & routing** — `multi-provider-prefix-routing`, `provider-retry-advice-ladder`, `websocket-session-pinned-runconfig`, `adapter-escape-hatch-kwargs`: prefix routing ladder, adapter-side retry classification feeding the runner vetoes, shared-transport pinned run-config sessions, escape-hatch kwargs merge with promote-and-pop.
- **Error recovery & nested tools** — `run-error-handler-recovery`, `agent-tool-result-cache`, `tool-failure-schema-bypass`: terminal-error recovery lane, nested-run caching protocol, schema-bypassing failure formatting.
- **Provider streaming layout** — `chatcmpl-stream-output-layout`: stable chunk-stream slot allocation.
- **ChatCompletions conversion** — `chatcmpl-assistant-turn-assembly`, `chatcmpl-tool-output-text-coercion`, `provider-reasoning-round-trip`, `chatcmpl-param-gating-headers`: item↔message state machine, tool-output text ladder, reasoning emit/replay round trip, endpoint-gated request params + header override.
- **Token accounting & context budget** — `usage-ledger-aggregation`, `tool-output-trimmer-window`, `usage-serialize-roundtrip`: guarded usage ledger, budgeted non-destructive output trimming, version-tolerant ledger wire format.
- **Tracing usage projection** — `usage-span-projection`, `run-lifecycle-span-lifecycle`: three-granularity span usage shapes with snapshot deltas and zero-guards; task/turn/agent/handoff span lifecycle across normal, handoff, and exception teardown.
- **Resume reconciliation** — `resume-approval-reconciliation`, `resume-collector-lanes`, `computer-shell-execution-lanes`: approval re-validation and stale-run rebinding for interrupted-turn resume; the generic non-function collector lanes (shell/apply_patch/custom) with per-type adapters; computer/local-shell execution with output-exists idempotence and incremental position-ordered commits.
- **AnyLLM adapter plane** — `anyllm-provider-plane`, `anyllm-transport-sanitize-close`, `anyllm-chat-path`, `anyllm-chat-request-construction`: capability-gated API/provider cache/normalization plus transport-kwargs, replay sanitization, close discipline, the chat-completions path (usage synthesis, content-filter refusal, span-before-yield, tool-message ordering repair), and the full request-assembly order with per-provider header routing.
- **Durable record process** — `ledger-reconciliation-protocol`: missed-pass ledger recovery with disk-truth verification and scoped own-row edits.

## Extending the foundation
Add one `references/<seam>.md` capsule per graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
OpenAI Agents Python (MIT), `main@fe45b415` (advanced from `cb8a2e7e` this pass; drift = 51 src files incl. the mined planes); Codebase Memory project `openai-agents-python` (28,851 nodes / 209,203 edges, ready, re-indexed 2026-08-24 at fe45b415, parse_partial = 3 files — none in mined modules). Pass 1 ([DONE:104]) swept the three legacy prose refs into 11 capsule-v2. Pass 2 (sweep-rover lane, HEAD unchanged at cb8a2e7e) executed ALL queued next-pass targets — `run_internal/run_loop.py`, `session_persistence.py`, `model_retry.py`, `tool_planning.py`, `streaming.py`, `strict_schema.py`, `_tool_identity.py`, `memory/` — whole-file reads adding 23 capsule-v2 (11→34). Pass 3 (legacy-sweep lane, [DONE:340]) re-pinned to fe45b415 and executed the pass-1 queue remainder — `items.py` whole-file, `run_internal/items.py` whole-file (drop_orphan/normalize/dedupe-prefering-latest ladders), `memory/openai_responses_compaction_session.py` whole-file (run_compaction modes) — plus diff-first mining of this wave's behavior fixes (b354ef0 approval-ownership relink, 1a55d70 max-turns latch, 89fab0f blocked-message customization, 042d84a+3e67155 MCP manager hygiene, 8cd1f5e created_by funnel), +13 capsule-v2 (34→47). Every decisive citation verified against source at fe45b415; all 13 Probes executed byte-exact GREEN (battery oaa-p3-probes.py); coverage stdin-JSON ×12 cited paths no_recorded_issue at generation 2026-08-24T03:12:31Z. Pass 4 (miner-openai-agents-python lane, HEAD unchanged at fe45b415) mined the previously-uncited models-provider/recovery/tool-failure planes — multi_provider.py, _openai_retry.py+retry.py advice side, run_error_handlers.py+run_internal/error_handlers.py, agent_tool_state.py, tool.py failure formatter + tool_execution bypass/nested resolution, chatcmpl_stream_handler.py output layout — adding 6 capsule-v2 (47→53) and creating the missing work record (state/research/verification) plus ledger row repair. Coverage ×16 cited paths no_recorded_issue at generation 2026-08-24T14:05:06Z.  Pass 10 (miner-openai-agents-python lane, HEAD unchanged at fe45b415) mined the non-streamed/streamed turn-twin divergence (defer_llm_end_hooks), streamed terminal-response assembly + retry-usage folding, any_llm _fetch_chat_response request construction, and the computer/local-shell execution lanes — adding 4 capsule-v2 (79→83). Codebase Memory MCP not connected (sixth consecutive pass); direct source+test reading fallback per AGENTS.md. Source and its tests remain authoritative; the graph is a discovery index, not truth.

Pass 5 (miner-openai-agents-python lane, HEAD unchanged at fe45b415) executed all six recorded next-pass targets as a deep-learning batch: whole-file reads of `chatcmpl_converter.py` (1002 ln) split into three seams (assistant-turn assembly state machine, tool-output text-coercion ladder, provider-reasoning emit/replay round trip incl. `reasoning_content_replay.py`), plus `responses_websocket_session.py` (pinned run-config protocol), lifecycle hook pairing + `util/_asyncio_tasks.gather_with_cancel` error precedence, `usage.py` ledger aggregation + `_build_response_usage`, `extensions/tool_output_trimmer.py`, and `handoffs/history.py` summary nesting — adding 8 capsule-v2 (53→61). Coverage ×21 cited paths no_recorded_issue at generation 2026-08-24T14:05:06Z.

Pass 6 (miner-openai-agents-python lane, HEAD unchanged at fe45b415) executed five of the six recorded next-pass targets: `handoffs/history.py` parser tail + writer pairing (numbered-record transcript parse ladder), `models/chatcmpl_helpers.py` endpoint-gated request params + cross-adapter `HEADERS_OVERRIDE` merge, `run_internal/oai_conversation.py` server-conversation delta tracker with the rewind-before-replay / re-mark-after-success cycle, `usage.py` serialize/deserialize round-trip shapes, and `run_internal/turn_resolution.py` final-output/handoff hook pairing — adding 5 capsule-v2 (61→66). Codebase Memory MCP was not connected in this session; Gate 2/3 ran on the direct source+test reading fallback per AGENTS.md (recorded in verification.md).

Pass 7 (miner-openai-agents-python lane, HEAD unchanged at fe45b415) executed five of the six recorded next-pass targets: `turn_resolution.py` tool-not-found detection + fail-soft formatter ladder, `turn_resolution.py` final-output-from-tools dispatch, `oai_conversation.py` hydrate_from_state resume seeding with unsent-tool-call-id skips, the `run_internal/items.py` + `result.py` nested-history ownership rebase lane (filter/reconcile/rebase with ambiguity rejection), and the litellm/any_llm escape-hatch kwargs forwarding plane (carried from pass 5) — adding 5 capsule-v2 (66→71). The usage span-projection seam was read but deferred to the next pass. Codebase Memory MCP was not connected in this session; Gate 2/3 ran on the direct source+test reading fallback per AGENTS.md (recorded in verification.md).

Pass 8 (miner-openai-agents-python lane, HEAD unchanged at fe45b415) executed all three recorded next-pass targets as four capsules: `usage.py` span projection (`model_usage_to_span_usage`/`turn_usage_to_span_data`/`task_usage_to_span_data`/`total_usage_to_span_metadata` :434–496) + `attach_usage_to_span` zero-guard/dispatch + `usage_delta` with all seven finally-block call sites; `turn_resolution.py` `resolve_interrupted_turn` approval-reconciliation core (`_snapshot_function_run` :1641, `_coerce_approval_call` :1739, fail-closed validation gate :1788, `_rebind_function_run` :2103, per-call ladder :2121–2248, nested sweep :2249–2300, `_approved_tool_invocation_status` pre-validation :2327) + `_select_function_tool_runs_for_resume` (tool_planning.py :883); the `any_llm_model.py` provider plane (`_split_model_name`, `_selected_api` capability ladder, `_get_provider` two-key cache + retry-disable clone, Google role normalization, `_normalize_response`/`_normalize_chat_chunk`); and the transport/sanitize/close plane (private `_aresponses` kwargs escape, recursive replay sanitizer, shield-and-detach stream close) — adding 4 capsule-v2 (71→75). Codebase Memory MCP was not connected in this session; Gate 2/3 ran on the direct source+test reading fallback per AGENTS.md (recorded in verification.md).

Pass 9 (miner-openai-agents-python lane, HEAD unchanged at fe45b415) executed the top three pass-8 next-pass targets as four capsules: the non-function resume collector lanes (`tool_planning.py` `_collect_runs_by_approval` :759–833 with the shell/apply_patch/custom adapter closures and call sites in `turn_resolution.py` :2364/:2377/:2390), the any-LLM chat path (`_get_response_via_chat` :571–706, `_stream_response_via_chat` :707–795, `_populate_chat_generation_span` :796–826, `_normalize_any_llm_message` :224–252, `_fix_tool_message_ordering` :1515–1611), the run-lifecycle span lifecycle (`run.py` task/agent span creation, handoff close, error attachment, and teardown :786/:956/:1400/:1451/:2096/:2123/:2188; `run_loop.py` turn spans :1734–1784; `turn_resolution.py` handoff_span :578–601), and a process capsule recording the pass-8 ledger-row reconciliation protocol. Adding 4 capsule-v2 (75→79). Codebase Memory MCP was not connected for a fifth consecutive session; direct source+test reading fallback per AGENTS.md (recorded in verification.md).

## Full view (memory graph)
Revalidate `openai-agents-python` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt guardrail parallelism, typed handoffs, the resolution ladder, parallel-tool failure arbitration, versioned run-state, the turn-loop/streaming persistence contracts, session rewind/admission semantics, retry replay-safety vetoes, tool-plan approvals, strict-schema conversion, the replay sanitizer + item identity/weakref protocols, orphan-pruning/dedupe input normalization, responses.compact mode/rollback/replay contracts, the schema-1.17 ownership relink, MCP manager/error-content hygiene, the ChatCompletions item↔message conversion state machine with reasoning round-trip gating, pinned-run-config shared transports, gather-with-cancel hook/cancellation precedence, guarded usage ledgers, budgeted tool-output trimming, summary-nested handoff history with a round-trippable transcript parser, endpoint-gated request params with contextvar header override, conversation delta tracking with rewind/re-mark retry cycles, version-tolerant usage wire formats, concurrent run/agent hook pairing, fail-soft missing-tool error ladders, closed tool-stop policy ladders, source-aware tracker hydration, mutation-proof ownership rebasing, and fixed-precedence escape-hatch kwargs merging, span-type-dispatched usage projection with snapshot deltas, fail-closed resume approval reconciliation with nested-state rebinding, capability-gated adapter API selection with two-key provider caching, subtractive replay sanitization with shielded stream-close discipline, generic non-function resume collector lanes with per-type adapters, chat-completions usage synthesis with content-filter refusal promotion and span-before-yield streaming, snapshot-delta span lifecycle across task/turn/agent/handoff teardown, and disk-truth scoped ledger reconciliation; adapt provider tool schemas, transports, and store backends; omit sampling/API-key specifics, provider-specific error semantics, realtime/, voice/, tracing/, sandbox/ internals (docker/unix_local planes uncited), examples/, and the OpenAI-server-side conversation registry internals (client-side tracking is covered).
