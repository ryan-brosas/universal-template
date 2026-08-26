<!-- capsule-v2 -->
# call-llm-safe-retry-ladder — What is the universal LLM failure contract, and why does it return "" instead of raising?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How do all agent roles survive transient API failures, and what must callers assume about the return value?

## Retry wrapper seam
**Path/Symbol:** `gui_agents/s3/utils/common_utils.py:call_llm_safe` (:35-56); transport-level backoff at `gui_agents/s3/core/engine.py` (`@backoff.on_exception(backoff.expo, (APIConnectionError, APIError, RateLimitError), max_time=60)` on every engine.generate — 9 sites, e.g. :39-41).
**Signature:** `call_llm_safe(agent, temperature=0.0, use_thinking=False, **kwargs) -> str`.
**Data Shape:** Two retry layers: engine backoff covers connection/rate errors for up to 60s; call_llm_safe adds a 3-attempt loop asserting the response is not None. Return is ALWAYS a str — `""` after exhausted retries.

### Decisive source
```python
while attempt < max_retries:
    try:
        response = agent.get_response(temperature=temperature, use_thinking=use_thinking, **kwargs)
        assert response is not None, "Response from agent should not be None"
        break
    except Exception as e:
        attempt += 1
        if attempt == max_retries:
            print("Max retries reached. Handling failure.")
    time.sleep(1.0)
return response if response is not None else ""
```

**Flow:** caller → get_response (engine may already have backed off internally) → exception or None ⇒ 1s sleep, retry ≤3 → success returns text; exhaustion returns "".
**Invariant:** (1) Never raises — every agent role (worker generator/reflection, grounding model, text-span agent, code agent, summary agent, narrator, judge) calls through this single seam, so no role can crash the episode loop. (2) The "" return IS a real state callers handle: CodeAgent raises RuntimeError("LLM returned empty response") on empty (code_agent.py :156-159); the worker's funnel turns unparseable plans into wait turns. (3) A 1s sleep runs even after the FINAL failed attempt — the last call pays latency for nothing (port-worthy quirk to fix consciously). (4) use_thinking toggles generate_with_thinking on engines that implement it (mllm.py :355-361).
**Probe:** `grep -n 'max_retries = 3' gui_agents/s3/utils/common_utils.py` → :39 (and :72 for the format loop's independent cap).
**Probe:** `grep -c 'backoff.on_exception' gui_agents/s3/core/engine.py` → 9.
**Probe:** `grep -n "RuntimeError(error_msg)" gui_agents/s3/agents/code_agent.py` → :159.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "call_llm_safe retries temperature", limit: 5 });
```

## Verdict
Adopt two-layer retry (transport exponential backoff + bounded semantic retry) with an error-as-empty-string contract; adapt caps and sleeps; omit print-based logging in favor of your logger. Porters who need fail-fast semantics should NOT reuse this wrapper around code agents without adding the emptiness check.
