<!-- capsule-v2 -->
# format-checker-reprompt-loop — How are malformed plans corrected without polluting the real history?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How does the reprompt-on-bad-format loop work, and why does it operate on a messages COPY?

## Format gate seam
**Path/Symbol:** `gui_agents/s3/utils/common_utils.py:call_llm_formatted` (:59-127); checkers in `gui_agents/s3/utils/formatters.py` (:10-58); wiring at `gui_agents/s3/agents/worker.py` (:310-319).
**Signature:** `call_llm_formatted(generator, format_checkers, **kwargs) -> str`; checker = `Callable[[str], Tuple[bool, str]]` returning (success, feedback).
**Data Shape:** Shipped worker checkers: `SINGLE_ACTION_FORMATTER` (exactly one `agent.*(...)` call inside the fenced block) and `CODE_VALID_FORMATTER(agent, obs)` partial (the block must eval successfully against the ACI — a DRY-RUN of the action funnel). Judge-side checkers: `THOUGHTS_ANSWER_TAG_FORMATTER`, `INTEGER_ANSWER_FORMATTER`.

### Decisive source
```python
messages = generator.messages.copy()   # scratch transcript for retries
while attempt < max_retries:
    response = call_llm_safe(generator, messages=messages, **kwargs)
    feedback_msgs = [fb for ok, fb in (c(response) for c in format_checkers) if not ok]
    if not feedback_msgs:
        break
    messages.append({"role": "assistant", "content": [{"type": "text", "text": response}]})
    formatting_feedback = f"- {delimiter.join(feedback_msgs)}"
    messages.append({"role": "user", "content": [
        {"type": "text",
         "text": PROCEDURAL_MEMORY.FORMATTING_FEEDBACK_PROMPT.replace("FORMATTING_FEEDBACK", formatting_feedback)}]})
```

**Flow:** copy live transcript → generate → run every checker → all pass ⇒ return; else append the bad response AS ASSISTANT plus one user feedback message (template replaces the FORMATTING_FEEDBACK token) and retry, max 3 attempts; exhausted ⇒ return last response anyway.
**Invariant:** (1) The REAL agent.messages never receives failed attempts — retries are invisible to subsequent turns except through the final accepted response. (2) CODE_VALID_FORMATTER means validation actually executes the funnel once during checking; a plan that survives this gate cannot fail at exec time (the later try/except is belt-and-suspenders). (3) On exhaustion the malformed response still flows downstream — callers must tolerate it. (4) kwargs["messages"] passthrough lets judges drive fully synthetic transcripts (behavior_narrator.py :259-264).
**Probe:** `grep -n 'generator.messages.copy()' gui_agents/s3/utils/common_utils.py` → :77.
**Probe:** `grep -n 'FORMATTING_FEEDBACK_PROMPT' gui_agents/s3/utils/common_utils.py gui_agents/s3/memory/procedural_memory.py` → :112 and template def :7-10.
**Probe:** `grep -c 'FORMATTER = lambda' gui_agents/s3/utils/formatters.py` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "call_llm_formatted format_checkers feedback", limit: 5 });
```

## Verdict
Adopt copy-transcript format-checker reprompt loops with (success, feedback) checker tuples — cheap structured-output enforcement without JSON mode; adapt checker set to your output grammar; omit the exact prompt wording. Note the deliberate cost trade: the code-valid checker re-runs grounding-model calls on every retry.
