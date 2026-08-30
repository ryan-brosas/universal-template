<!-- capsule-v2 -->
# CJK-aware token estimation — how do you pre-price a prompt you can't tokenize cheaply?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** What character heuristic should gate reservations when the text is mostly Chinese and running a real tokenizer per request is too costly?

## Script-split estimate with deliberate high bias
**Path/Symbol:** `backend/app/services/ai_usage.py` `estimate_token_count` :93–108 (+ floors `calculate_reservation_tokens` :110–115, `ASYNC_TASK_MIN_TOKENS`/`MODULE_RESERVATION_MIN_TOKENS` :33–49, `estimate_async_task_tokens`).
**Signature:** `estimate_token_count(*texts: str | None) -> int`; `calculate_reservation_tokens(module: str, input_tokens: int) -> int`.
**Data Shape:** In: any number of strings (None→""). Out: int ≥ 1. Module tables map module key → minimum reserved tokens (async tasks 10k; sync modules 1.2k–10k).

### Decisive source
```python
non_ascii_chars = sum(1 for char in combined if ord(char) > 127)
ascii_chars = len(combined) - non_ascii_chars
# CJK text is commonly close to one token per character, while Latin text
# is closer to four characters per token. This intentionally errs high.
return max(1, non_ascii_chars + math.ceil(ascii_chars / 4))
```
```python
def calculate_reservation_tokens(module, input_tokens):
    minimum = MODULE_RESERVATION_MIN_TOKENS.get(module_key, 1200)
    return max(minimum, max(0, int(input_tokens or 0)) * 3)   # 3× input as headroom
```

**Flow:** concat inputs → split by `ord(char) > 127` → CJK counts 1 token/char, Latin 4 chars/token, ceil up → reservation = max(module floor, 3× estimate). Async task estimates additionally floor at the module's async minimum so queue-time pricing never under-funds a run.
**Invariant:** The estimate NEVER feeds user-visible billing totals — actuals are measured after the call (`record_ai_usage` re-estimates output from real text); it only sizes the hold. Err-high is a feature: an undersized hold turns into a 429 mid-task, an oversized one just settles back down.
**Probe:** `backend/tests/test_ai_quota_rules.py::test_reservation_math_*` family — pure-function assertions on the floor/max ladder (`calculate_reservation_tokens`, `evaluate_platform_quota`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "estimate_token_count", limit: 5 });
// verified line-exact: ai_usage.py :93–108
```

## Verdict
Adopt the two-bucket script-split heuristic wherever CJK content meets prepaid quota (also good for cost previews); adapt bucket ratios to your tokenizer mix; omit tiktoken-based exactness. Direct tests green in `tests.test_ai_quota_rules` (real runner).
