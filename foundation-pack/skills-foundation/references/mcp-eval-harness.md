<!-- capsule-v2 -->
# MCP Eval Harness — how is an MCP server's tool surface graded end-to-end by an LLM agent?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What does the reference MCP evaluation loop measure, how are answers extracted, and what makes a score trustworthy?

## QA-pair agent loop with tag-scraped exact-match grading
**Path/Symbol:** `skills/mcp-builder/scripts/evaluation.py` — `agent_loop` (:86–151), `evaluate_single_task` (:154–184), `extract_xml_content` (:79–83), `run_evaluation` (:220–272); transports via `connections.create_connection` (stdio/sse/http).
**Signature:** `agent_loop(client, model, question, tools, connection) -> tuple[str, dict[str, {count, durations[]}]]`; `score: int(response_value == qa_pair["answer"])`.
**Data Shape:** eval file = XML with `.//qa_pair` → `{question, answer}`. The system prompt (`EVALUATION_PROMPT`, :21–53) mandates three tagged outputs — `<summary>` (steps, tools used in order, inputs/outputs per tool), `<feedback>` (names/params/descriptions/errors critique + WHY each improvement helps), `<response>` (final answer; `NOT_FOUND` sentinel; numeric/ID answers as bare values; response LAST). Extraction takes the LAST regex match per tag (DOTALL).

### Decisive source
```python
while response.stop_reason == "tool_use":
    tool_use = next(block for block in response.content if block.type == "tool_use")
    ...
    try:
        tool_result = await connection.call_tool(tool_name, tool_input)
        tool_response = json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)
    except Exception as e:
        tool_response = f"Error executing tool {tool_name}: {str(e)}\n"
        tool_response += traceback.format_exc()   # errors become CONTEXT, never abort the eval
    ...
    if tool_name not in tool_metrics:
        tool_metrics[tool_name] = {"count": 0, "durations": []}
    tool_metrics[tool_name]["count"] += 1
    tool_metrics[tool_name]["durations"].append(tool_duration)
```
```python
"actual": response_value,
"score": int(response_value == qa_pair["answer"]) if response_value else 0,
```

**Flow:** parse qa_pairs → connect (transport-agnostic; headers parsed `Key: Value`, env `KEY=VALUE`) → per task: fresh message list → create with tools → while stop_reason == tool_use: execute ONE tool call (first tool_use block), append tool_result (errors stringified with traceback into the conversation), record per-tool count+duration metrics → final text scraped for `<response>` → exact string match vs expected → markdown report with accuracy %, avg duration, avg tool calls/task, plus per-task summary+feedback verbatim.
**Invariant:** Tool failures are DATA — the traceback goes back to the model so it can recover, and the run continues; an eval that dies on the first tool error measures nothing. Scoring is deliberately brittle EXACT match, which is only safe because the prompt pins answer FORMAT (bare number / bare ID / exact text / NOT_FOUND) — format-pinning and exact-match are a PAIRED contract; loosening one silently breaks the other. Per-tool latency histograms (not just totals) localize which tool is slow. Sync SDK calls wrapped in asyncio.to_thread keep one event loop across transports.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c 'traceback.format_exc()' skills/mcp-builder/scripts/evaluation.py` = 1; `grep -cF 'response_value == qa_pair["answer"]' skills/mcp-builder/scripts/evaluation.py` = 1 (use -F: the bracket expression is regex-active).
**Coverage caveat:** live-LLM harness; deterministic probes only.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "skills", query: "agent_loop", limit: 5 });
// skills.skills.mcp-builder.scripts.evaluation.agent_loop Function evaluation.py 86-151
```

## Verdict
Adopt for any tool-server evaluation: tag-structured agent output, error-as-context continuation, per-tool metric histograms, exact-match scoring protected by format-pinned prompts, transport-swappable connection factory. Adapt models/transports; do not soften exact-match without replacing the format contract.
