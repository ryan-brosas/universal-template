<!-- capsule-v2 -->
# Critique-input DOM scrubbing — why does the critic see "DOM successfully fetched" instead of megabytes of page content?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you feed a verification agent everything it needs to judge progress WITHOUT blowing its context on DOM payloads?

## Two-layer placeholder filter: string rewrite for display, typed message rebuild for history
**Path/Symbol:** `core/orchestrator.py`:`filter_tool_interactions_for_critique` (`:99-132`), `filter_dom_messages` (`:135-167`), `extract_tool_interactions` (`:52-92`), `ensure_tool_response_sequence` (`:23-48`).
**Signature:** `def filter_tool_interactions_for_critique(tool_interactions_str: str) -> str`; `def filter_dom_messages(messages) -> list`.
**Data Shape:** Tool interactions are flattened to `"Tool Call: <name>\nArguments: <args>\nResponse: <content>\n---\n"` blocks keyed by tool_call_id. The two filters target DOM tools `{get_dom_text, get_dom_fields}` only.

### Decisive source
```python
# layer 1 — string level, for the critique PROMPT:
if "Tool Call: get_dom_text" in interaction or "Tool Call: get_dom_fields" in interaction:
    for line in lines:
        if line.startswith("Tool Call:") or line.startswith("Arguments:"):
            filtered_lines.append(line)
        elif line.startswith("Response:"):
            filtered_lines.append("Response: DOM successfully fetched")
            break                    # stop processing: drops ALL remaining response lines
...
return "---\n".join(filtered_interactions) + ("---\n" if filtered_interactions else "")

# layer 2 — typed level, for the BROWSER's next-turn history:
new_part = ToolReturnPart(tool_name=part.tool_name,
                          content="DOM successfully fetched",
                          tool_call_id=part.tool_call_id, ...)
filtered_messages.append(ModelRequest(parts=[new_part], kind='request'))
```
Companion validator `ensure_tool_response_sequence` walks planner messages and RAISES ValueError listing unresponded tool_call_ids BEFORE calling the model — an API-crash guard so a half-finished history can't poison the next request.
**Flow:** BA new_messages → extract interactions (call+response pairs by id) → string-filter for CA prompt; separately, stored BA history gets every DOM tool-return rebuilt with placeholder content before being passed to the NEXT `BA_agent.run`.
**Invariant:** The two layers are NOT redundant: the string filter protects the critic's prompt budget; the typed rebuild protects the BROWSER's own future turns (pydantic-ai replays real message objects). Both must keep call ids intact or the provider rejects the sequence. The break-after-placeholder matters: DOM responses span many lines and truncating mid-block leaves orphan fragments that look like real data.
**Probe:** No tests (coverage caveat). Graph pins: `trace_path --function-name run --direction outbound` lists all four helpers as direct callees of the loop body; `ensure_tool_response_sequence` is applied ONLY to the planner lane (`orchestrator.py:320`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "filter dom messages tool interactions critique", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt dual-layer DOM elision (prompt-string + stored-history rebuild) whenever a verifier agent shares tool output with an executor. Adapt the tool-name set and placeholder text. Omit nothing in the line-break semantics — partial filtering leaks DOM into the critic.
