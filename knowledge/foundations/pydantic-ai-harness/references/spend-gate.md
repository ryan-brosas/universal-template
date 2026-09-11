<!-- capsule-v2 -->
# Spend gate — the local, immediate per-response money gate that stops a runaway loop before the next request

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a harness stop an agent once a money/period/tenant budget is spent, when `UsageLimits` only caps tokens/requests for one run?

## SpendLimits capability
**Path/Symbol:** `pydantic_ai_harness/spend/_capability.py` — `SpendLimits(AbstractCapability[AgentDepsT])`, `SpendCallback`, `PriceFunc`; `_snapshot.py` (`SpendSnapshot`, `BudgetStatus`, `Spent`); `_exceptions.py`.
**Signature:** `SpendLimits(budgets=[Budget(...)], callback=None, price=None, unpriced='zero'|'raise', ...)`.
**Data Shape:** prices each response with `ModelResponse.cost()`, adds it to every configured window, and refuses the next request once a window is spent. `PriceFunc` returns `None` to fall back to the `genai-prices` registry. `_RUN_SCOPED_WINDOWS = ('run','conversation')`; `_UNPRICED_POLICIES = frozenset({'zero','raise'})`.

### Decisive source
```python
# The gate is local and immediate. Provider usage APIs and observability
# backends aggregate after the fact and are read by polling, so a number there
# moves only once the requests behind it have already been made -- enough to
# reconcile a counter, not enough to stop the request a runaway loop is about
# to make.
```

**Flow:** per model response → price → add to each window key → if any window spent, raise `SpendLimitExceeded` (refuse next request). A `SpendCallback` is called after each response with what it cost and where the budgets stand.
**Invariant:** the gate is local and immediate, never polled; a shared counter across worker processes must be backed by a shared store (e.g. Redis `_redis.py`); `unpriced='zero'` treats unpriced responses as free, `'raise'` raises `UnpricedModelError`.
**Probe:** `tests/spend/test_spend.py` (1,479L) and `tests/spend/test_temporal.py` pin per-window accumulation, refusal-on-spent, and the unpriced policies.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "SpendLimits SpendLimitExceeded PriceFunc SpendCallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the local per-response money gate keyed by budget windows; adapt the pricing source and store backend; omit host-specific tenant/worker wiring. This is the runtime twin of the `spend-budget-keys` config contract.
