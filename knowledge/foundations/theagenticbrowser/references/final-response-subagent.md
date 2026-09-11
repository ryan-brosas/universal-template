<!-- capsule-v2 -->
# Final-response sub-agent — why does the critique agent own a second LLM, and what does it do with "compiled successfully" answers?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you guarantee the user receives the ACTUAL answer instead of a success-sounding summary when a browser agent reports completion?

## Critique-owned `final_response` tool_plain delegating to a dedicated answer-extraction LLM
**Path/Symbol:** `core/agents/critique_agent.py:113-118` (`@CA_agent.tool_plain final_response`) → `core/skills/final_response.py:get_response` (`:39-57`).
**Signature:** `async def final_response(plan: str, browser_response: str, current_step: str) -> str` / `async def get_response(plan: str, browser_response: str, current_step: str) -> str`.
**Data Shape:** The CA's structured output contract (`result_type=CritiqueOutput` = `{feedback, terminate, final_response}`) is enforced by pydantic-ai; the final_response TOOL is plain-string-in/string-out. `get_response` builds ONE user prompt `f"Plan: {plan}\n\nBrowser Response: {browser_response}\n\nCurrent Step: {current_step}\n\n"` and calls the chat completions API directly with `max_tokens=4000`.

### Decisive source
```python
# critique_agent.py :113-118 — the ONLY tool on the critique agent
@CA_agent.tool_plain
async def final_response(plan: str, browser_response: str, current_step: str) -> str:
    response = await get_response(plan, browser_response, current_step)
    return response

# final_response.py system-prompt rules (:26) — the anti-fabrication gate:
#   'If the Browser Agent has responded like "I have compiled the information
#    successfully", but not included the actual information inside the response,
#    then you need to tell the Critique Agent that the actual information is
#    missing and you should retry getting the information needed from Browser Agent.'
```
**Flow:** CA decides termination → its system prompt FORBIDS generic answers ("information has been compiled" is explicitly banned in BOTH agents' prompts) → when the raw browser text looks like a success stub rather than content, the CA calls the `final_response` tool → a SECOND model call re-reads plan + full browser response + current step and extracts/composes the literal answer (reports as headings/sub-points, never literal tables — rules :28-29) → that string becomes both `critique_response.data.final_response` and the value returned to the user by the orchestrator.
**Invariant:** Termination and answer-production are decoupled: the critique model decides WHEN, the sub-agent decides WHAT. The orchestrator returns `critique_response.data.final_response` unchanged (:590) — if the CA fills that field from its own summarization instead of routing through the tool, the anti-stub rule has no second chance to catch it. `max_tokens=4000` exists precisely so long compiled reports survive extraction. This is the repo's answer to "browser agents that say done but say nothing."
**Probe:** `grep -c tool_plain core/agents/critique_agent.py` → `1` (exactly one tool); `grep -n "max_tokens=4000" core/skills/final_response.py` → `49`; `grep -c "from core.skills.final_response import get_response" core/agents/critique_agent.py` → `1`. Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "final response get_response critique tool", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: termination/answer decoupling via a critique-owned extraction sub-call, plus the explicit ban on success-stub phrasings in both prompt layers. Adapt: the OpenAI-specific client wiring and logfire logging. Omit: nothing load-bearing. Coverage caveat: no upstream tests; probes are line-pinned greps at pin `71daa28`.
