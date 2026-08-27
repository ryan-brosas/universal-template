---
name: agno-foundation
description: "Use when building or porting an agent framework runtime — the single-agent run loop with retries/cancellation/HITL pauses/approvals and conversation time-travel (continue/fork/regenerate), model provider fallback and retry-with-guidance, OR the multi-agent layer: a supervisor/team-leader loop over member agents, an autonomous shared-task-list mode, tool routing for the leader model, cooperative run cancellation with cancel-before-start support, and HITL pause propagation from members to teams. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---

# agno: Agent & Team Control-Plane Foundations

## Use this for
Use when building or porting an agent framework runtime: the single-agent run loop with retries/cancellation/HITL pauses/approvals and conversation time-travel (continue/fork/regenerate), model provider fallback and retry-with-guidance — OR the multi-agent layer: a supervisor/team-leader loop over member agents, an autonomous shared-task-list mode, tool routing for the leader model, cooperative run cancellation with cancel-before-start support, and HITL pause propagation from members to teams. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump

### Team / supervisor plane
- `references/supervisor-run-spine.md` — ordered 13-step async leader loop; which failure classes retry vs terminate.
- `references/task-list-fsm.md` — blocked/failed dependency cascade that guarantees plan-loop termination.
- `references/task-mode-loop.md` — autonomous plan→delegate→observe iteration with dual exit keys.
- `references/cancel-before-start-registry.md` — setdefault-vs-blind-write cancellation intent + member drain bucket.
- `references/delegate-message-bus.md` — member event streaming, drain-don't-break, cascade-cancel mid-flight.
- `references/parallel-fanout-backpressure.md` — deepcopy-per-branch isolation + cancel piercing through `gather`.
- `references/tool-routing-table.md` — fixed assembly order, mode-exclusive delegation/task tools, first-wins dedupe.
- `references/background-manager-chaining.md` — per-retry memory/learning tasks: cancel-then-await, never leak.
- `references/member-resolution-hitl.md` — nested member finders (deep vs route) + pause propagation contract.
- `references/closure-capture-fanout.md` — default-arg binding regression suite for loop-spawned delegates.

### Run-control / models-core plane
- `references/run-loop-retry-ladder.md` — How does the synchronous agent run loop order its stages and retry without losing background work?
- `references/dispatch-entry-validation.md` — What must be validated and initialized before a run can start?
- `references/cancel-before-start-intent.md` — How does cancellation survive the race where cancel() arrives before register()?
- `references/redis-nx-cancellation.md` — How is the same intent-preservation guaranteed atomically across processes?
- `references/cancel-wins-over-pause.md` — Why must cancelling a paused run clear its pause flags before persisting?
- `references/pair-safe-truncation-index.md` — How do you cut a transcript mid-run without orphaning a tool call?
- `references/fork-fresh-metrics.md` — Why does a forked run need its metrics/events/timer wiped?
- `references/regenerate-always-forks.md` — What exactly does regenerate drop, and why does it always create a new run_id?
- `references/hitl-tool-update-ladder.md` — How does the resume dispatch route each paused tool kind back into execution?
- `references/pause-stamp-and-store.md` — What is the exact pause exit sequence when a tool needs human action?
- `references/tool-assembly-pipeline.md` — How do declared, default, and client tools become model-ready Functions with media injected?
- `references/approval-idempotent-stamping.md` — How are approval records created exactly once across double-fired pause hooks?
- `references/background-futures-disconnect.md` — What must always happen in the run-loop finally block, even on success?

### Models-core resilience plane
- `references/model-fallback-taxonomy.md` — Which provider errors may fall back to another model, and which must surface?
- `references/model-fallback-ladder.md` — error-specific fallback lists; 4xx auth errors never masked.
- `references/retry-with-guidance.md` — transient sleep-retry vs teach-retry via temporary guidance messages.
- `references/error-taxonomy-late-classify.md` — idempotent late classification of provider errors (message beats status).

## Capsule map

**Team / supervisor plane**
- **Run spine** — `supervisor-run-spine`: register→session→retry-loop(13 steps)→cleanup/store; guardrail+cancel errors bypass retries; CancelledError persists via detached task.
- **Plan state** — `task-list-fsm`: five-state TaskList; unknown dep fail-closed; failed dep auto-fails dependents so `all_terminal()` exits the loop.
- **Autonomy loop** — `task-mode-loop`: `<current_task_state>` injection per iteration; exit on goal_complete OR all-terminal-clean; max_iterations exhaustion is not an error.
- **Cancellation** — `cancel-before-start-registry`: `cancel_run` stores intent pre-registration; `register_run` setdefaults (setdefault-vs-blind-write intent); 5s-bounded delegate-task drain before persist; member drain bucket + facade swap mechanism.
- **Message bus** — `delegate-message-bus`: capture final output, always forward terminal events, suppress ordinary events while draining after cascading cancel into the child.
- **Backpressure** — `parallel-fanout-backpressure`: deepcopy session_state + media per branch; re-raise RunCancelledException out of `gather(return_exceptions=True)`; pause returns task to pending.
- **Tool routing** — `tool-routing-table`: user tools → flag-gated built-ins → mode-exclusive delegation XOR task tools; duplicate names keep FIRST registration (documented update_user_memory trap).
- **Background work** — `background-manager-chaining`: new attempt cancels-and-awaits previous memory/learning tasks; success joins via await_for_open_threads; finally cancels survivors.
- **Members & HITL** — `member-resolution-hitl`: recursive deep finder vs top-level route finder; pause copies requirements, fills identity blanks, keeps live `_member_run_response`.
- **Concurrency correctness** — `closure-capture-fanout`: default-arg freeze of loop variables in fan-outs; PR #6067 regression-pinned.

**Run-control plane**
- **Run loop** — `run-loop-retry-ladder`: attempts = retries+1 wrap the whole session-read→cleanup ladder; exponential backoff only between attempts; every exit path funnels through cleanup_and_store.
- **Dispatch entry** — `dispatch-entry-validation`: sync run rejects async DB loudly; hooks normalized once via `_hooks_normalised`; options precedence explicit args > existing context > resolved defaults.
- **Cancellation intent** — `cancel-before-start-intent`: dict `setdefault(run_id, False)` so intent stored pre-registration survives; cancel returns was_registered.
- **Cancellation (Redis)** — `redis-nx-cancellation`: SET NX preserves intent; pipeline EXISTS+SET makes cancel atomic; TTL bounds stale keys.
- **Cancellation × pause** — `cancel-wins-over-pause`: cancelled runs keep only resolved requirements; paused tools get all three pause flags cleared so the persisted row cannot re-pause on resume.
- **Time travel** — `pair-safe-truncation-index`: boundary snaps DOWN to the nearest index that keeps every kept tool_call answered; tools/requirements pruned to surviving tool_call_ids.
- **Time travel** — `fork-fresh-metrics`: fork deep-clones then resets metrics/timer/created_at/events and mints forked_from_* lineage fields.
- **Time travel** — `regenerate-always-forks`: regenerate drops only trailing no-tool-call assistant messages; it derives fork=True and raises if the caller passes fork explicitly.
- **HITL** — `hitl-tool-update-ladder`: one four-case ladder (confirm → external → get_user_input/ask_user → user-input schema) drives resume execution for both stream and non-stream paths.
- **Pause exit** — `pause-stamp-and-store`: paused runs JOIN background futures + merge metrics BEFORE persisting a self-contained row (approvals stamped, content synthesized); pause is an exit, not an internal wait.
- **Lifecycle** — `background-futures-disconnect`: finally cancels memory/learning/culture futures and disconnects connectable tools; client-disconnect persists cancelled runs on detached asyncio tasks.
- **Tools** — `tool-assembly-pipeline`: flag-gated composition (factories → client → memory/learning defaults → knowledge) then parse + signature-driven CONDITIONAL media injection; async entrypoints raise at resolution time in sync mode.

**Models-core resilience plane**
- **Model failover** — `model-fallback-ladder`: specific list (rate-limit/context-overflow) beats general on_error; 400-4xx minus {429,529} returns None; primary error re-raised when all fail; appended messages synced back via seed_len diff.
- **Model failover (agent side)** — `model-fallback-taxonomy`: error-classified list selection + `_clean_kwargs_for_fallback` strips `temporary` guidance messages; per-attempt message copies; `fallback_model_activated` stream event.
- **Teach-retry** — `retry-with-guidance`: RetryableModelProviderError appends temporary guidance user message and recurses (limit 1); transient errors sleep with optional exponential backoff; non-retryable raises immediately.
- **Error taxonomy** — `error-taxonomy-late-classify`: classify() at decision time; {429,529}→rate-limit; 13 context-window substrings beat status codes; idempotent.
- **Approvals** — `approval-idempotent-stamping`: pause hook stamps approval_id on tools; second fire short-circuits returning the stamped id; pending approvals raise RuntimeError at continue-gate.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question against project `ext-agno`. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
agno (`libs/agno`), Apache-2.0, `main@9644f22982ae017eaa4ad85c561d927d9ac03119` (= base_sha); Codebase Memory project `ext-agno` (58,651 nodes / 394,936 edges, FULL mode, generation 2026-08-23T09:21:21Z, generation_matches; parse_partial ×2 uncited files only). Pass 1 mined the team/run/models-core planes whole-file ([DONE:271], commit ab88858a). Pass 2 mined the agent run-control plane whole-file (agent/_run.py, agent/_tools.py, run/approval.py, run/cancellation_management/, models/fallback.py, utils/message.py) at the SAME pin.

## Full view (memory graph)
Revalidate `ext-agno` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Caveat: closure-scoped tool names (`adelegate_task_to_member`, `execute_tasks_parallel`) do not resolve in BM25 search_graph — retrieve via their factories (`_get_delegate_task_function`, `_get_task_management_tools`) or Module nodes. Function/method nodes resolve line-exact elsewhere (verified pass 2: safe_truncation_index :10-47, acreate_approval_from_pause :209-271, FallbackConfig members).

## Boundaries
Adopt the control-flow contracts: failure-class handler split, cancel-intent preservation, drain-don't-break streaming, deepcopy-per-branch isolation, first-wins tool dedupe, late error classification; plus the agent-plane contracts: pair-safe transcript truncation, regenerate⇒fork derivation, requirement-resolution algebra, idempotent approval stamping, terminal-cancel invariant, error-classified fallback with 4xx no-masking. Adapt storage/session types, db/redis clients, provider adapters, and prompt wording to your host. Omit agno product surface: AgentOS HTTP routes, 50+ model-provider wrappers, vectordb/knowledge implementations, cookbook examples, telemetry.
