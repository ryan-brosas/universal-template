<!-- capsule-v2 -->
# WatsonX completion clamp — how do you keep `max_completion_tokens` positive near a full context window WITHOUT the clamp becoming sticky?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When the prompt nearly fills the window, how do you shrink the completion budget per-call without permanently shrinking it for the client's lifetime?

## clamp_watsonx_completion_for_messages + first-seen budget stash
**Path/Symbol:** `src/cuga/backend/cuga_graph/utils/token_counter.py:357-438` (`clamp_completion_tokens`, `_ORIGINAL_BUDGET_ATTR`, `clamp_watsonx_completion_for_messages`), constants :26-27 (`WATSONX_PROMPT_SAFETY_MARGIN = 0.20`, `WATSONX_COMPLETION_BUFFER = 1024`).
**Signature:** `clamp_watsonx_completion_for_messages(model: Any, messages: list) -> None` (mutates `llm.params["max_completion_tokens"]` in place); `clamp_completion_tokens(context_size, prompt_tokens, requested, *, buffer=256) -> int`.
**Data Shape:** accepts dicts (`role`/`content`) or LangChain messages; walks `.bound` chains to unwrap bound models; no-op unless the innermost model is a `ChatWatsonx`.

### Decisive source
```python
# Inflate: our estimator undercounts vs IBM's real tokenizer on dense/JSON-heavy prompts.
prompt_tokens = int(raw_prompt_tokens * (1 + WATSONX_PROMPT_SAFETY_MARGIN))

params = dict(llm.params or {})
# Resolve from the first-seen budget: params["max_completion_tokens"] is the key
# this function writes below, so re-reading it would make any clamp sticky for
# the client's lifetime (object.__setattr__ bypasses pydantic's field guard).
requested = getattr(llm, _ORIGINAL_BUDGET_ATTR, None)
if requested is None:
    requested = (getattr(llm, "max_completion_tokens", None) or getattr(llm, "max_tokens", None)
                 or params.get("max_completion_tokens") or 16000)
    object.__setattr__(llm, _ORIGINAL_BUDGET_ATTR, requested)
```

**Flow:** unwrap `.bound` chain → type check → ensure profile/context size → count prompt tokens with the approximate counter → inflate ×1.20 → resolve requested budget ONCE from attrs/params/16k default and stash on the client via a private attribute (attribute lifetime = client lifetime; an id()-keyed module cache could outlive the client and collide on id reuse) → `clamped = max(1, context - inflated_prompt - buffer)` when that's below requested → write back into a COPIED params dict → warn loudly with raw/inflated counts.
**Invariant:** (1) never read back the value you wrote — resolve the requested budget from the first-seen stash or every turn clamps further (ratchet-to-one bug); (2) the estimator UNDERCOUNTS IBM's real tokenizer ~20% on JSON-heavy prompts, so sizing against raw estimates still hits watsonx's "max_tokens must be at least 1"; (3) clamp floor is 1, never ≤0; non-watsonx models are untouched.
**Probe:** no direct unit test (coverage caveat — deterministic check: call twice with a huge prompt; second call must compute the same `requested` as the first because of the stash). Downstream watsonx behavior is exercised by sdk tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "clamp_watsonx_completion_for_messages max_completion_tokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the first-seen-budget stash + inflation margin + max(1, …) floor verbatim for any provider that rejects tiny completion budgets — the sticky-clamp trap is provider-independent; adapt the margin/buffer numbers to your tokenizer gap; omit the ChatWatsonx/dict-message handling for other providers. Coverage caveat: source-read verified; the invariant is documented in-code where the test would assert it.
