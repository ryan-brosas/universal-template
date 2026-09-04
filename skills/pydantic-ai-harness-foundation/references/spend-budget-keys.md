<!-- capsule-v2 -->
# Spend budget keys — a window produces a key, nobody resets counters

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a multi-window spend budget count against the right bucket without reset jobs, and how are configs validated against their failure mode at construction?

## Budget-as-keys
**Path/Symbol:** `pydantic_ai_harness/spend/_budget.py` (265L) — `store_key`, `bucket`, `scope_key`, `Budget.__post_init__`; `BudgetSpec` TypedDict.
**Signature:** `store_key = name | window | scope | bucket`; `Budget(name, window, scope, ceiling, ...)`.
**Data Shape:** "A window decides the key a budget counts against and nothing else — a new day is a new key." Rollover = key change; there are no reset jobs.

### Decisive source
```python
# Separator is '|' NOT ':' — colons appear inside model references and tenant ids.
# WINDOW IS PART OF THE KEY even though buckets look disjoint: a run whose id
# happens to be 'total' would otherwise share a counter with a 'total' budget.
# Only the FIRST THREE separators delimit; name/window/scope are validated
# separator-free, so bucket needs no check even though consumer ids may contain anything.
```

**Flow:** each priced response is added to every configured window's key; a window is refused once its ceiling is spent. TTL table: run 24h, conversation 30d, day 48h, month 62d, total None — "long enough that a conversation reaching it cannot practically be resumed."
**Invariant:** `__post_init__` rejects configs that "would quietly misbehave": ceiling ≤ 0 (exhausted-before-start); NaN caught via `usd.is_finite()` BEFORE the `<= 0` comparison (which raises InvalidOperation); infinity passes but reads as unreachable ceiling; `warn_at` without a ceiling can never fire → error; a misspelt `'forevr'` retain literal is rejected AT CONSTRUCTION; scope callables are TYPE-CHECKED not coerced (str() on an int-typed tenant id would mint a fresh counter per run); returning the reserved `'*'` scope or containing `|` is refused.
**Probe:** `tests/spend/test_spend.py` (1,479L) pins key composition, TTL behavior, validation failure modes, and scope resolution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "store_key Budget __post_init__ BudgetSpec", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt budgets-as-keys (no reset jobs), `|`-separated key with window embedded, and validate-config-against-failure-mode at construction; adapt the TTL horizons; omit host-specific store backends. Pure-counter budgets (no usd/tokens) accumulate and report but never block.
