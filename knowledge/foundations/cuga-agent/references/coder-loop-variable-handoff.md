<!-- capsule-v2 -->
# Coder loop variable hand-off — how does generated code's result become a named variable the planner can reference?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What exact contract must an LLM-written script's stdout follow so its output is stored as a first-class agent variable, and what happens when the last line isn't JSON?

## Last-JSON-line capture with fallback status variable
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/api/code_agent/code_agent.py:CodeAgent.get_last_nonempty_line` (:48-89), `extract_code_from_response` (:111-148), `run` (:150-229); consumer `src/cuga/backend/cuga_graph/nodes/api/api_code_agent.py:ApiCoder.node_handler` (:32-52).
**Signature:** `get_last_nonempty_line(text: str, limit=5) -> tuple[dict, str]`; `CodeExecutor.eval_for_code_agent(code=..., state=...)` (already-mined executor seam).
**Data Shape:** success shape `{"variable_name": str, "description": str, "value": Any}` as the final stdout line; failure fallback `{"variable_name": "output_status", "value": <full execution output>}`.

### Decisive source
```python
        out, remaining_text = self.get_last_nonempty_line(execution_output, limit=5)
        steps_summary = []
        if out:
            steps_summary = [remaining_text]

        if not out:
            out = {
                "variable_name": "output_status",
                "value": execution_output,
            }
            logger.warning("Not json output")
```
and the scanner that makes the trailing line optional:
```python
        for i, line in enumerate(reversed(lines)):
            if count >= limit:
                break
            ...
                json_lines = json.loads(stripped_line)
                json_line_index = len(lines) - 1 - i
                remaining_lines = lines[:json_line_index]
                return json_lines, "\n".join(remaining_lines)
        return "", text
```

**Flow:** chain (raw-text mode `wx_json_mode="no_format"`) → `extract_code_from_response` merges ALL fenced blocks into one script, dropping a leading language-identifier line when it has no space → execute → scan up to 5 bottom lines for valid JSON → on hit, everything above the JSON line becomes `steps_summary` and the dict registers via `variables_manager.add_variable(name, description, value)` → optional `summarize_steps` LLM summary (`features.code_output_summary`, output truncated to 50000 chars) → `CodeAgentOutput` JSON message. `ApiCoder.node_handler` then writes a bounded `variables_summary` (max_length=5000) plus `final_output` back into `api_planner_history[-1].agent_output` and returns to APIPlannerAgent.
**Invariant:** The variable NAME comes from model-controlled stdout — never from code identifiers — so the planner can only reference what was actually printed. No-JSON does NOT fail the run; it degrades to an `output_status` variable holding raw logs, keeping the planner loop alive. `extract_code_from_response` returns the ORIGINAL text unchanged when no fences exist (a bare-script fallback).
**Probe:** Recorded upstream gap at HEAD (executor-side tests exist separately). Deterministic probe of the pure function: `cd $REFERENCE_ROOT/agents/cuga-agent && python3 -c "import ast,json; src=open('src/cuga/backend/cuga_graph/nodes/api/code_agent/code_agent.py').read(); assert 'get_last_nonempty_line' in src and 'output_status' in src"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "CodeAgent get_last_nonempty_line extract_code_from_response eval_for_code_agent", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the print-a-final-JSON-dict protocol with bounded look-back and the non-failing `output_status` degradation; adopt history-summary bounds that keep prompts small. Adapt execution transport (the already-capsuled CodeExecutor plane). Omit the AppWorld-specific summary prompt wiring.
