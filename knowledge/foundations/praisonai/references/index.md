<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# praisonai: Agent chat-and-tool-execution kernel

## Use this for
Use when building or porting an agent runtime's completion call path and its reliability ladder: hook gates around LLM dispatch, budget enforcement, error classification into recovery actions, streaming fallbacks, bounded tool retry with circuit breaking, loop detection, and guardrail validation/regeneration. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./completion-recovery-ladder.md` — how does one sync completion call turn a provider failure into exactly one recovery action without unbounded recursion?
- `./budget-guard.md` — how is a max_budget made a genuine hard cap rather than one overshootable by a whole LLM call?
- `./before-llm-hook-gate.md` — how do blocking hooks/plugins refuse an LLM dispatch instead of failing open?
- `./streaming-fallback-routing.md` — which exceptions may trigger the non-streaming fallback, and which must never?
- `./tool-retry-ladder.md` — when does a failed tool call get retried, and what must always short-circuit the retry?
- `./circuit-breaker-scoping.md` — how is a shared breaker registry prevented from cross-agent contamination and stale-id reuse?
- `./loop-detection-detectors.md` — how does a sliding window of hashed tool calls distinguish stuck loops from legitimate repetition?
- `./guardrail-fail-closed-regen.md` — how does a guardrail retry regenerate with feedback while its LLM judge fails closed on ambiguity?

## Capsule map
- **Completion recovery ladder** — `completion-recovery-ladder`: classify_llm_error picks ONE of compress-context retry, fallback-model chain, or bounded backoff; model swap restored in `finally`.
- **Budget guard** — `budget-guard`: pre-call projected-cost refusal plus post-call lock-guarded accumulation with stop/warn/callback policy.
- **BEFORE_LLM hook gate** — `before-llm-hook-gate`: blocked plugin results return a refusal string; hook-mutated messages are adopted in place for the real call.
- **Streaming fallback routing** — `streaming-fallback-routing`: only "Streaming is not supported" ValueError downgrades to non-streaming; ToolExecutionError re-raises to prevent double tool execution.
- **Tool retry ladder** — `tool-retry-ladder`: RetryPolicy precedence tool > agent > default; denial keys, non-idempotent declarations, and last attempts return immediately.
- **Circuit-breaker scoping** — `circuit-breaker-scoping`: per-agent-instance key `tool_{id(self)}_{fn}`, GC finalizer closes id-reuse window, denials are not breaker failures.
- **Loop detection** — `loop-detection-detectors`: canonicalized args-hash sliding window feeding poll_no_progress / ping_pong / generic_repeat detectors with warn→critical levels.
- **Guardrail regen + fail-closed judge** — `guardrail-fail-closed-regen`: bounded regeneration prompt carrying the validator error; ambiguous judge replies validate False through both entry points.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
praisonai (MIT), `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory project `praisonai` (FULL mode, gen 2026-08-25T22:51:56Z, 83,901 nodes / 511,677 edges, 0 skipped; 25 parse-partial files are helm yaml/html fixtures/pytest.ini — none cited; `src/praisonai-agents/praisonaiagents/db` excluded by design).

## Full view (memory graph)
Revalidate `praisonai` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt pure contracts: recovery-action classification, retry/denial vocabularies, breaker scoping rules, detector thresholds, fail-closed validation semantics. Adapt host-specific integration: litellm/openai client plumbing, `_unified_dispatcher` cache invalidation, stream_emitter event names, ExecutionConfig backoff fields. Omit product behavior: praisonai CLI/session/db packages, telemetry dashboards, helm deploy templates, and the async twin (`_achat_impl`) until a later pass confirms parity.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`before-llm-hook-gate.md`](./before-llm-hook-gate.md)
- [`budget-guard.md`](./budget-guard.md)
- [`circuit-breaker-scoping.md`](./circuit-breaker-scoping.md)
- [`completion-recovery-ladder.md`](./completion-recovery-ladder.md)
- [`guardrail-fail-closed-regen.md`](./guardrail-fail-closed-regen.md)
- [`loop-detection-detectors.md`](./loop-detection-detectors.md)
- [`streaming-fallback-routing.md`](./streaming-fallback-routing.md)
- [`tool-retry-ladder.md`](./tool-retry-ladder.md)
