<!-- capsule-v2 -->
# ReAct parser — how is free LLM text turned into Action/Finish, and what does json_repair fix without inventing data?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** What are the exact ReAct grammar rules, error ladders, and JSON-repair guardrails?

## parse / _safe_repair_json / _extract_thought
**Path/Symbol:** `lib/crewai/src/crewai/agents/parser.py:62-128` (`parse`), `:131-146` (`_extract_thought`), `:161-184` (`_safe_repair_json`); regexes + messages in `agents/constants.py`.
**Signature:** `def parse(text: str) -> AgentAction | AgentFinish` raising `OutputParserError(error)`.
**Data Shape:** `AgentAction(thought, tool, tool_input, text, result=None)`; `AgentFinish(thought, output: str|BaseModel, text)`. Regexes tolerate numbered variants: `Action\s*\d*\s*:\s*(.*?)\s*Action\s*\d*\s*Input\s*\d*\s*:\s*(.*)` (DOTALL).

### Decisive source
```python
if includes_answer:                      # "Final Answer:" wins over any Action
    final_answer = text.split(FINAL_ANSWER_ACTION)[-1].strip()
    if final_answer.endswith("```"):
        count = final_answer.count("```")
        if count % 2 != 0:               # unbalanced fences → strip the closer
            final_answer = final_answer[:-3].rstrip()
    return AgentFinish(...)

def _safe_repair_json(tool_input: str) -> str:
    if tool_input.startswith("[") and tool_input.endswith("]"):
        return tool_input                    # arrays passed through untouched
    tool_input = tool_input.replace('"""', '"')
    result = repair_json(tool_input)
    if not result or result in UNABLE_TO_REPAIR_JSON_RESULTS:   # '""', '{}'
        return tool_input
    # "json-repair >= 0.60 wraps non-JSON input in a single-element list;
    #  treat that as unrepairable and return the original."
    if result.startswith("[") and not tool_input.lstrip().startswith("["):
        return tool_input
    return str(result)
```

**Flow:** Extract thought (`text[:index of "\nAction"` else `"\nFinal Answer"`, backtick-stripped) → Final Answer branch → Action branch (clean `*`-wrapped names, repair input) → else error ladder: no `Action:` at all → MISSING_ACTION_AFTER_THOUGHT message; has Action but no Input → MISSING_ACTION_INPUT message; else generic format-without-tools slice. The two self-correction messages are themselves fed back as the user message on retry (`handle_output_parser_exception` appends `{"role":"user","content":e.error}` and returns an empty-tool AgentAction so the loop continues).
**Invariant:** Repair must be conservative: `{}`/`""` count as FAILURE results (a repaired-to-empty dict would call the tool with no args), and version-dependent wrap-in-list output is rejected — otherwise non-JSON inputs silently become `[...]` strings. `Final Answer` detection uses substring split, so it beats a co-occurring Action block; the executor additionally warns when the answer string contained "Final Answer:" but parsing produced an AgentAction.
**Probe:** Deterministic: `python3 - <<'EOF'` style check impossible per no-script rule — instead pin by grep anchors at this pin: `grep -n 'UNABLE_TO_REPAIR_JSON_RESULTS' lib/crewai/src/crewai/agents/parser.py` → lines 20,176; `grep -n 'count % 2 != 0' lib/crewai/src/crewai/agents/parser.py` → line 99. Parser behavior exercised via `TestCallLLM.test_call_llm_parser_error` in `tests/agents/test_agent_executor.py`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "parse ReAct AgentAction AgentFinish", limit: 6, detail: "ids" });
```

## Verdict
Adopt the grammar, error-message-as-retry-prompt loop, and conservative repair guards verbatim; adapt the regexes if your prompt uses different markers; omit numbered-action tolerance only with evidence your models never emit them.
