<!-- capsule-v2 -->
# Tool-call salvage regex — what happens when a provider returns a function call as plain text?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How does the agent recover tool calls when the inference vendor fails to parse them into structured `tool_calls`?

## Fallback parse of `{...}` from message.content with parameters/arguments dual-key tolerance
**Path/Symbol:** `os_computer_use/llm_provider.py:144-168` (`OpenAIBaseProvider.call`, tools branch).
**Signature:** `call(messages, functions) -> (content|None, [ {type:"function", name, parameters} ])`.
**Data Shape:** Salvaged call = same `create_tool_call` shape as native ones; `parameters` may arrive under EITHER key (`parameters` preferred, `arguments` fallback). Malformed JSON arguments are dropped SILENTLY from native calls by the comprehension guard.

### Decisive source
```python
combined_tool_calls = [
    self.create_tool_call(tool_call.function.name, parse_json(tool_call.function.arguments))
    for tool_call in tool_calls
    if parse_json(tool_call.function.arguments) is not None   # malformed args silently dropped
]
# Sometimes, function calls are returned unparsed by the inference provider. This code parses them manually.
if message.content and not tool_calls:
    tool_call_matches = re.search(r"\{.*\}", message.content)
    if tool_call_matches:
        tool_call = parse_json(tool_call_matches.group(0))
        parameters = tool_call.get("parameters", tool_call.get("arguments"))
        if tool_call.get("name") and parameters:
            combined_tool_calls.append(self.create_tool_call(tool_call.get("name"), parameters))
            return None, combined_tool_calls     # content deliberately suppressed
```

**Flow:** native `tool_calls` present → parse+filter (bad JSON vanishes, no error surfaces) → zero native calls AND non-empty text → greedy `\{.*\}` span → json.loads via `parse_json` (None on JSONDecodeError, printed) → accept only when BOTH `name` and parameters resolve → return `(None, [call])`.
**Invariant:** Salvage fires ONLY when there are no native tool calls; a salvaged call REPLACES content (`return None, …`) so the loop never treats prose as both thought and action; `parse_json` returning None anywhere degrades to "no tool calls this turn" rather than raising.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && grep -n 'tool_call.get' os_computer_use/llm_provider.py && grep -n 're.search' os_computer_use/llm_provider.py` (pins dual-key `.get` chain at :161 and the single salvage regex at :157).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "parse_json tool_call arguments re.search salvage", limit: 6, fields: ["signature", "name", "file"] });
// expect OpenAIBaseProvider.call + module-level parse_json
```

## Verdict
Adopt the salvage ladder (native-first, text-fallback, dual key names, silent-drop bad args) for any small/local-model tool loop where providers under-parse; adapt the regex to your models' emission habits; omit the silent drop if you need telemetry on malformed calls.
