<!-- capsule-v2 -->
# token-usage-cost-gate — How is spend reported when multiple providers are in play?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** Where is cost computed, what gates it, and what falls back when pricing is unavailable?

## Token accounting seam
**Path/Symbol:** `gpt_engineer/core/token_usage.py:TokenUsageLog.update_log` (:193), `is_openai_model` (:251-260), `usage_cost` (:273-297); consumer `gpt_engineer/applications/cli/main.py:552-557`.
**Signature:** `update_log(messages, answer, step_name)`; `usage_cost() -> float | None`.
**Data Shape:** Per-step TokenUsage records (prompt/completion tokens via tiktoken for OpenAI names, char-heuristic otherwise); cumulative totals; cost via langchain-openai's get_openai_token_cost_for_model.

### Decisive source
```python
def is_openai_model(self) -> bool:
    return "gpt" in self.model_name.lower()

def usage_cost(self) -> float | None:
    if not self.is_openai_model(): return None
    try:
        result = 0
        for log in self.log():
            result += get_openai_token_cost_for_model(self.model_name, log.total_prompt_tokens, is_completion=False)
            result += get_openai_token_cost_for_model(self.model_name, log.total_completion_tokens, is_completion=True)
        return result
    except Exception as e:
        print(f"Error calculating usage cost: {e}")
        return None
```
```python
# main.py terminal report:
if ai.token_usage_log.is_openai_model():
    print("Total api cost: $ ", ai.token_usage_log.usage_cost())
elif os.getenv("LOCAL_MODEL"):
    print("Total api cost: $ 0.0 since we are using local LLM.")
else:
    print("Total tokens used: ", ai.token_usage_log.total_tokens())
```

**Flow:** every AI.next logs tokens keyed by step_name → end-of-run three-way report: gpt*⇒USD cost (pricing-table lookup, exception-safe to None) | LOCAL_MODEL env ⇒ hardcoded $0 | other ⇒ raw token count.
**Invariant:** (1) Cost requires BOTH name-substring "gpt" AND successful pricing lookup — unknown/new gpt models degrade to printed error + None rather than crash. (2) Local-model detection is ENV-VAR trust ("LOCAL_MODEL"), not endpoint inspection — spoofable but simple. (3) update_log is called INSIDE AI.next AFTER backoff success only — failed/retried calls don't double-count. (4) step_name threading (curr_fn() everywhere) makes per-step attribution possible in format_log().
**Probe:** `grep -c '"gpt" in self.model_name.lower()' gpt_engineer/core/token_usage.py` → 1 (:258 name gate).
**Probe:** `grep -c 'return None' gpt_engineer/core/token_usage.py` → 2 (:283 non-OpenAI gate, :297 pricing-exception fallback).
**Probe:** `grep -n 'is_openai_model\|total_tokens' gpt_engineer/applications/cli/main.py | tail -4` → the report branch.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "TokenUsageLog usage_cost update_log is_openai_model", limit: 10 });
```

## Verdict
Adopt name-gated cost + env-trust local detection + graceful None for any multi-provider agent; adapt pricing source; note tiktoken absent ⇒ estimate path (num_tokens_from_messages falls back heuristically).
