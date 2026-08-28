<!-- capsule-v2 -->
# XML tool-call parse twin — how do you parse a stop-sequence-truncated tool call and repair the conversation in place?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; direct source reads (Codebase Memory MCP not connected this session). **Question:** When an LLM's tool call is cut off by a stop sequence, how do you parse it anyway and keep the message history consistent?

## chat.py registry parse + modify_utils tolerant wrapper vs the agent_utils Tool-list twin
**Path/Symbol:** `sweepai/core/chat.py:tool_call_parameters` (:157–165), `parse_function_call_parameters` (:168–174), `parse_function_calls` (:178–198), `sweepai/agents/modify_utils.py:validate_and_parse_function_call` (:625–640); twin `sweepai/agents/agent_utils.py:parse_function_calls` (:71–88) + `validate_and_parse_function_call` (:91–104); `continuous_llm_calls` stop behavior `sweepai/core/chat.py:663–712`.
**Signature:** `parse_function_calls(response_contents: str) -> list[dict]` (registry form) / `(response_contents: str, tools: list[Tool]) -> list[dict]` (Tool-list form); `validate_and_parse_function_call(function_calls_string: str, chat_gpt: ChatGPT) -> AnthropicFunctionCall | None`.
**Data Shape:** tool_call = `{"tool": name, "arguments": {param: text}}`; parameters missing from the response are simply ABSENT from the dict (no parse-time error — validation is the caller's job).

### Decisive source
```python
def validate_and_parse_function_call(function_calls_string: str, chat_gpt: ChatGPT) -> AnthropicFunctionCall:
    function_calls = parse_function_calls(
        function_calls_string.strip("\n") + "\n</function_call>"      # tolerant close-tag append
    )
    if len(function_calls) > 0:
        function_calls[0] = AnthropicFunctionCall(
            function_name=function_calls[0]['tool'],
            function_parameters=function_calls[0]['arguments'],
        )
        if "<function_call>" in function_calls_string:
            chat_gpt.messages[-1].content = (                            # in-place message repair
                chat_gpt.messages[-1].content.rstrip("\n") + "\n</function_call>"
            )
    return function_calls[0] if len(function_calls) > 0 else None
```
**Flow:** `continuous_llm_calls` stops generation AT `"</function_call>"` without including it, so every tool-call string arrives truncated → the wrapper appends the missing close tag BEFORE parsing, making truncation a non-event → the registry parser iterates known tool names, regexes `<tool>(.*?)</tool>` DOTALL, then per-param `<param>(.*?)</param>`; only the FIRST call is returned → crucially the wrapper also patches `chat_gpt.messages[-1].content` in place so the stored assistant message matches what was parsed — the next round's context is self-consistent without a re-render → `agent_utils.py` is a structural twin for the @tool-decorator agents: same regex shape, but the registry is a `list[Tool]` and the wrapper takes `tools` as an argument; FOUR near-identical NO_TOOL_CALL_PROMPT copies exist (modify_utils:97, agent_utils:132, search_agent:127, question_answerer:699) — copy drift is real.
**Invariant:** Parsing must be tolerant of the stop-sequence contract (the close tag is never in the text) and the conversation must be repaired in place so history stays byte-consistent with what was executed. Missing parameters are a VALIDATION failure, not a parse failure — the parse layer returns what it found; the dispatcher (handle_function_call) turns absence into teaching errors. A port that validates inside the parser loses the ability to distinguish "malformed" from "incomplete" and teaches the model nothing.
**Probe:** No offline test at pin. Deterministic probes executed: `grep -n "def parse_function_calls" sweepai/core/chat.py sweepai/agents/agent_utils.py` → chat.py:178, agent_utils.py:71; `grep -n "validate_and_parse_function_call" sweepai/agents/modify.py` → :6(import),:125,:158,:248; `grep -rn "validate_and_parse_function_call" sweepai/chat/api.py` → :19(import),:663; `grep -n 'strip("\\n") + "\\n</function_call>"' sweepai/agents/modify_utils.py sweepai/agents/agent_utils.py` → modify_utils.py:628, agent_utils.py:93; `grep -n "NO_TOOL_CALL_PROMPT = " sweepai/agents/modify_utils.py sweepai/agents/agent_utils.py sweepai/agents/search_agent.py sweepai/agents/question_answerer.py` → :97/:132/:127/:699; `grep -n '"make_change":' sweepai/core/chat.py` → :158.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "parse_function_calls validate_and_parse_function_call tool_call_parameters stop_sequences function_call", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// chat.py:157-198/:663-712, modify_utils.py:625-640, agent_utils.py:40-145 at pin
// substituted — see verification.md pass 9.
```
## Verdict
Adopt the tolerant-parse + in-place-repair pair: append the stop-sequence tail before parsing, patch the stored message to match, keep validation in the dispatcher. Adapt the registry to your host's tool declaration mechanism (decorator, schema, or manifest). Omit: the four-copy NO_TOOL_CALL_PROMPT drift — keep ONE parameterized template. Coverage caveat: no offline test at pin; behavior is pinned only by the probe set above.