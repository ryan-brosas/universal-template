<!-- capsule-v2 -->
# Budget guard — how is a max_budget made a genuine hard cap rather than one overshootable by a whole LLM call?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** How does an agent enforce a dollar ceiling so that (a) a call that would breach it is refused *before* dispatch, and (b) post-call accounting is thread-safe and policy-driven (stop / warn / callback)?

## ChatMixin._chat_completion pre-call projection + post-call accumulation
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/chat_mixin.py:ChatMixin._chat_completion` (pre-call guard lines 1803–1826; post-call enforcement lines 1932–1958; async parity twin lines 2506–2524 and 2610–2635). Estimator: `praisonaiagents/agent/tool_execution.py:ToolExecutionMixin._estimate_min_call_cost` (lines 1472–1514). Init: `agent.py` lines 2348–2353 (`_max_budget`, `_on_budget_exceeded`, `_cost_lock = threading.Lock()`, `_total_cost = 0.0`). Exception: `praisonaiagents/errors.py:BudgetExceededError` (line 185+).
**Signature:** `_estimate_min_call_cost(self, messages, max_tokens=None) -> float`; guard state: `_max_budget: Optional[float]`, `_on_budget_exceeded: "stop" | "warn" | callable(cost, budget)` (default `"stop"` from ExecutionConfig).

### Decisive source
```python
# Pre-call budget guard (zero overhead when _max_budget is None).
if self._max_budget and self._on_budget_exceeded == "stop":
    _est_min_cost = self._estimate_min_call_cost(
        messages, getattr(self, 'max_tokens', None)
    )
    with self._cost_lock:
        _projected_cost = self._total_cost + _est_min_cost
        _current_cost = self._total_cost
    if _projected_cost >= self._max_budget:
        raise BudgetExceededError(
            f"Agent '{self.name}' would exceed budget before call: "
            f"${_current_cost:.4f} + est ${_est_min_cost:.4f} >= "
            f"${self._max_budget:.4f}",
            budget_type="cost", limit=self._max_budget, used=_current_cost, agent_id=self.name
        )
...
# Post-call: Thread-safe cost tracking (Gap 1a fix)
with self._cost_lock:
    self._total_cost += _cost_usd
    self._total_tokens_in += _prompt_tokens
    self._total_tokens_out += _completion_tokens
    self._llm_call_count += 1
    budget_exceeded = self._max_budget and self._total_cost >= self._max_budget
    current_cost = self._total_cost
if budget_exceeded:
    if self._on_budget_exceeded == "stop":
        raise BudgetExceededError(...)
    elif self._on_budget_exceeded == "warn":
        logging.warning(f"[budget] {self.name}: ${current_cost:.4f} exceeded ${self._max_budget:.4f} budget")
    elif callable(self._on_budget_exceeded):
        self._on_budget_exceeded(current_cost, self._max_budget)
```

**Flow:** pre-call (only in `"stop"` mode): estimate this call's *minimum* cost from message content (~4 chars/token) plus an output reservation — explicit `max_tokens` if set, else `DEFAULT_OUTPUT_RESERVATION_TOKENS` when any input exists, else 0 — read `_total_cost` under `_cost_lock`, refuse with `BudgetExceededError` when projected >= cap → dispatch → post-call: accumulate cost/tokens/call-count in one lock section, evaluate breach inside the same section, then apply the policy ladder outside the lock: stop-raise / warn-log / user callback. The estimator is deliberately a *minimum* (message content only, no tool-schema tokens); reactive post-call accounting is the documented backstop.
**Invariant:** no LLM call may be dispatched whose projected cost breaches the ceiling in stop mode; all reads/writes of `_total_cost` happen under `_cost_lock`; warn mode never pre-blocks (reactive-only); a blocked call records zero spend; `BudgetExceededError` carries machine-readable `budget_type`/`limit`/`used`/`agent_id` (and still accepts the legacy positional `(agent_name, total_cost, max_budget)` constructor for backward compat).
**Probe:** `tests/unit/test_token_budget.py` pins both halves directly — `TestPreCallGuard.test_guard_blocks_before_dispatch` mocks `_chat_completion_with_retry` to explode if reached, asserts `BudgetExceededError` raised, `assert_not_called()`, and `_total_cost == 0.0`; `test_guard_skips_when_warn_mode` asserts the estimate alone would exceed the cap but warn mode must not pre-block; the async twin test (~line 330) does the same through `_execute_unified_achat_completion`; `TestPreCallEstimate` (:177–218) pins empty-input → 0.0, scaling with input, larger `max_tokens` reservation costing more, and the default output reservation keeping an unset-`max_tokens` estimate strictly > 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "budget guard estimate min call cost lock", name_pattern: "^_estimate_min_call_cost$|^BudgetExceededError$", limit: 10 });
```

## Verdict
Adopt the two-stage shape: pre-dispatch *projection* refusal (turns the cap into a hard ceiling instead of one overshootable by a whole call) plus post-call lock-guarded accumulation with a stop/warn/callback policy ladder evaluated inside the same critical section as the write. Adopt the minimum-estimate honesty (content-only, output reservation default) and the dual-constructor error type. Adapt the ~4-chars/token heuristic, litellm-based `_calculate_llm_cost`, and `DEFAULT_OUTPUT_RESERVATION_TOKENS` to your host's pricing. Omit the token/time budget variants of `BudgetExceededError` unless your host needs them. Coverage: no recorded index issue on cited paths; both guard halves are directly tested (this pass corrects pass-1's "no direct test" caveat — `tests/unit/test_token_budget.py` exists at the pin).
