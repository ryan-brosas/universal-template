<!-- capsule-v2 -->
# Budget enforcement plane — how do you stop an agent run from burning tokens/money without a try/except at every call site?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Where does cost/token enforcement live so every turn and tool call is gated exactly once, and what does the pricing math need to count cache tokens correctly?

## Model-aware BudgetTracker auto-wired as a PRE_TOOL_USE guard
**Path/Symbol:** `backend/python/app/agent_loop_lib/modules/providers/budget/tracker.py:BudgetTracker` (L11–109) + `modules/providers/budget/pricing.py:MODEL_PRICING/ModelPricing.cost_usd/get_pricing/get_context_window` (L8–83); wired at `control_plane/control_plane.py:262` and `:662–663`.
**Signature:** `BudgetTracker(max_input_tokens=None, max_output_tokens=None, max_tool_calls=None, max_turns=None, max_cost_usd=None, model=None)`; `async record_turn(input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0)` / `async record_tool_call()` / `async check() -> None` raises / `async snapshot() -> BudgetSnapshot`.
**Data Shape:** Plain counters incremented on record; `check()` compares with STRICT `>` (turn N of limit N passes). Cost derived on demand, never accumulated. `BudgetSnapshot` carries the six counters plus computed `cost_usd`.

### Decisive source
```python
# control_plane.py — construction pins the model BEFORE any call happens:
self._budget_manager = BudgetTracker(
    max_input_tokens=cfg.budget.max_tokens,
    max_tool_calls=cfg.budget.max_tool_calls,
    model=model,                      # pricing resolved once, per-model
)
# ...and AFTER the explicit hooks loop, the absence-check auto-add:
if self._budget_manager is not None and "budget_guard" not in cfg.hooks:
    kernel.on(HookEvent.PRE_TOOL_USE).use(require_budget(self._budget_manager))

# pricing.py — cache economics are ratios of the INPUT price, not separate rows:
CACHE_READ_MULTIPLIER = 0.10
CACHE_WRITE_MULTIPLIER = 1.25
def get_pricing(model):               # unknown/local/mock models never raise:
    input_price, output_price = MODEL_PRICING.get(model or "", _DEFAULT_PRICING)  # Sonnet-class fallback
```

**Flow:** ControlPlane.start() builds tracker (step 4 of the numbered pipeline) → registers `require_budget` either explicitly (`hooks=["budget_guard"]`) or via the absence check after all named hooks are installed → every PRE_TOOL_USE consults one shared manager → `check()` raises `BudgetExceeded` naming the exceeded limit → loop's existing degradation path handles it (no budget-specific catch sites).
**Invariant:** (1) Enforcement is a middleware over the ONE funnel, not scattered checks — a porter who adds per-loop `if budget:` branches reintroduces the bug this shape prevents (spawned children ride the same kernel). (2) Pricing must be resolved against the model the agent actually runs (constructor arg), with a non-raising fallback for unknown names — cost math failing on an unrecognized model string would kill real runs. (3) Cache-read/write tokens are first-class in BOTH recording and pricing; ignoring them under/over-states Anthropic-cache workloads ~10x/25%. (4) The same pricing table feeds CLI display — two copies drift.
**Probe:** `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py::TestBudgetAndTools` (:92 wires manager onto runtime; :101–103 record 600>500 tokens then expects `BudgetExceeded`; :238 guard requires a configured manager; :324 budget+allowlist AUTO-add when absent from hooks).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "BudgetTracker check BudgetExceeded require_budget", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the middleware-carried budget guard + absence-check auto-add + strict-> limit comparison + ratio-based cache pricing with Sonnet-class fallback. Adapt limit names/units to host config. Omit the hardcoded Claude/GPT price rows (stale by design; keep the table-as-single-source pattern). No coverage caveat: wiring, auto-add, and raise behavior all directly pinned.
