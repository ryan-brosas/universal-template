<!-- capsule-v2 -->
# Dead-format conversion twins — what pydantic-ai → OpenAI message converters exist, and which one actually runs?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** If you need pydantic-ai run results as OpenAI-format messages, which converter is live and what does the dead twin teach?

## Dict-based `convert_to_openai_messages` (uncalled) vs class-based `AgentConversationHandler` (live, orchestrator-owned)
**Path/Symbol:** `core/utils/convert_openai.py:1-62` (`convert_to_openai_messages`, whole file) vs `core/utils/openai_msg_parser.py:AgentConversationHandler` (`:22-217`, called from orchestrator :325/:424/:508/:542).
**Signature:** `def convert_to_openai_messages(pydantic_result)` (sync, dict-in/list-out) vs the handler's per-agent `add_*_message(response)` methods (mutate shared `conversation_history`).
**Data Shape:** Input = a dict with `"all_messages"` whose entries are `{kind: "request"|"response", parts: [...]}` with `part_kind` ∈ system-prompt/user-prompt/tool-return/text/tool-call; tool-call args resolved as `part["args"]["args_json" if "args_json" in part["args"] else "args_dict"]`.

### Decisive source
```python
# convert_openai.py :15-16, :35 — request/response walk over ALL messages at once
if message["kind"] == "request":
    for part in message["parts"]:
...
# :42-50 — response parts split into text_parts + tool_calls, then ONE assistant msg:
assistant_message = {"role": "assistant"}
if text_parts:
    assistant_message["content"] = "\n".join(text_parts)
if tool_calls:
    assistant_message["tool_calls"] = tool_calls

# openai_msg_parser.py :116-133 — the LIVE path instead fabricates a pseudo tool call:
tool_call_id = str(uuid.uuid4())
assistant_message = {'role': 'assistant', 'content': None,
    'tool_calls': [{'id': tool_call_id, 'type': 'function',
        'function': {'name': 'planner_agent',
            'arguments': json.dumps({'plan': plan, 'next_step': next_step})}}]}
```
**Flow (why two exist):** `convert_to_openai_messages` converts a pydantic-ai result's full message list faithfully but NOTHING calls it — grep-verified zero import sites. The live pipeline needs something stricter than conversion: planner/critique/ss turns must look like TOOL INTERACTIONS in the replayed transcript, so `AgentConversationHandler` synthesizes uuid-keyed pseudo tool-call/tool-result pairs per agent turn (planner_agent, ss_analyzer) and tags critique output with `name='critique_agent'`. Pass-1's unified-transcript-synthesis capsule owns that synthesis contract.
**Invariant:** Conversion ≠ synthesis. A faithful converter preserves what the framework emitted; a replayable transcript REIFIES each non-browser agent turn as an explicit tool call so OpenAI-format consumers see a valid alternation. If you port the converter, port its args_json/args_dict fallback too — pydantic-ai versions differ in which key they populate.
**Probe:** `grep -rn "convert_to_openai_messages" core/ --include='*.py' | wc -l` → `1` (definition only); `grep -n "args_json.*args_dict" core/utils/convert_openai.py` → `48`; `grep -c "verify_conversation" core/utils/open_ai_verfication_script.py` → `2`; `grep -c "temperature=0.7" core/utils/open_ai_verfication_script.py` → `1`; `grep -rn "ConversationVerifier\|open_ai_verfication" core/ --include='*.py' | grep -v open_ai_verfication_script.py | wc -l` → `0` (standalone utility, no wiring). Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "convert_to_openai_messages all_messages part_kind", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt: the args_json/args_dict fallback if you ever need raw pydantic-ai→OpenAI conversion; adopt ConversationVerifier as an optional offline transcript grader (fresh AsyncOpenAI client, temperature 0.7, max_tokens 500, error-as-data dict). Omit BOTH files from a behavioral clone of this pin — the live path is AgentConversationHandler pseudo-tool synthesis (already owned by pass-1's unified-transcript-synthesis capsule). Coverage caveat: no upstream tests.
