<!-- capsule-v2 -->
# Model-name alias ladder — how do you classify a reasoning model when vendors ship bare short aliases?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (DeepSeek profile); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Profile functions match model names by prefix — what happens when a deployment surface exposes a bare alias like `r1`, and how should alias sets evolve?

## deepseek-r1-alias-ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/profiles/deepseek.py:` `deepseek_model_profile` (:6–16, alias ladder at :8).
**Signature:** `def deepseek_model_profile(model_name: str) -> ModelProfile | None`.
**Data Shape:** three-way boolean classification feeding exactly three profile fields: `ignore_streamed_leading_whitespace=is_r1`, `supports_thinking=is_r1 or is_v4`, `thinking_always_enabled=is_r1`.

### Decisive source
```python
# BEFORE #7723:  is_r1 = model_name.startswith('deepseek-r1') or model_name == 'deepseek-reasoner'
# AFTER — Bedrock-style bare alias added FIRST in the OR chain:
is_r1 = (
    model_name == 'r1'
    or model_name.startswith('deepseek-r1')
    or model_name == 'deepseek-reasoner'
)
# V4 models (deepseek-v4-flash, deepseek-v4-pro, …) support thinking via reasoning_effort
# but do not always enable it — thinking_always_enabled stays False.
is_v4 = model_name.startswith('deepseek-v4-')
```

**Flow:** exact-match aliases (`==`) are checked before/alongside prefix matches (`startswith`); the r1 class gets streaming-whitespace tolerance + always-on thinking; v4 gets optional thinking only.
**Invariant:** three rules:
1. Bare deployment aliases (Bedrock ARN tails like `r1-v1:0`, gateway short names) are EXACT matches — never fold them into a prefix rule; `'r1'.startswith('deepseek-r1')` is False and a loose prefix like `'r'` would over-classify.
2. Alias additions are additive OR-clauses on ONE classification line; downstream profile fields derive from the booleans, so no other code moves (the whole fix is one line).
3. Classification order documents intent: exact aliases first (most specific), then family prefixes. Keep new vendor surfaces (Bedrock #7723, Vercel gateway via gateway-profile-routing-table) pointed at THIS function so alias knowledge lives in one place.
**Probe:** direct behavioral check EXECUTED this pass in repo `.venv`: `deepseek_model_profile('r1')` → `{supports_thinking: True, thinking_always_enabled: True, ignore_streamed_leading_whitespace: True}` vs `('chat')` → supports False; upstream pins: `tests/profiles/test_resolution_matrix.py::test_bedrock_deepseek_r1` (:750–763, asserts all four r1 fields incl. `bedrock_send_back_thinking_parts`; skipped locally for missing boto3) + resolution-matrix grep `grep -c "deepseek.r1-v1:0" tests/profiles/test_resolution_matrix.py` ≥ 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "deepseek_model_profile r1 alias is_r1", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exact-match-before-prefix alias classification with single-line additive evolution; adapt alias strings per vendor surface; omit nothing — the pattern IS the one-liner plus its placement discipline.
