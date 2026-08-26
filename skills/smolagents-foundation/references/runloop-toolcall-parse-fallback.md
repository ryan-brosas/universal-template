<!-- capsule-v2 -->
# Tool-calling parse fallback — how do providers that never emit native tool_calls still drive ToolCallingAgent?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** When `chat_message.tool_calls` is empty, what is the text-scraping fallback chain, and which malformed-JSON cases get dedicated coaching errors?

## JSON-blob scraping ladder
**Path/Symbol:** `src/smolagents/agents.py:ToolCallingAgent._step_stream` (:1327-1334); `Model.parse_tool_calls` (`models.py:583-594`); `get_tool_call_from_text` (:400-415); `parse_json_blob` (`utils.py:166-186`); `parse_json_if_needed` (:193-200).
**Signature:** `parse_tool_calls(message) -> ChatMessage` (mutates: forces role ASSISTANT, fills tool_calls); `parse_json_blob(json_blob) -> (dict, prefix)`; uuid4 id minted per scraped call.
**Data Shape:** Expects ONE JSON object in the text with keys `tool_name_key="name"` / `tool_arguments_key="arguments"`; missing name key → ValueError listing actual keys.

### Decisive source
```python
# utils.py :169-181 — first-{ to last-} slice with a dedicated multi-call coaching error:
first_accolade_index = json_blob.find("{")
last_accolade_index = [a.start() for a in list(re.finditer("}", json_blob))][-1]
json_str = json_blob[first_accolade_index : last_accolade_index + 1]
json_data = json.loads(json_str, strict=False)     # strict=False tolerates control chars
...
if json_blob[place - 1 : place + 2] == "},\n":
    raise ValueError(
        "JSON is invalid: you probably tried to provide multiple tool calls in one action. PROVIDE ONLY ONE TOOL CALL.")
```

**Flow:** `_step_stream`: if the provider returned no structured tool_calls → `model.parse_tool_calls(chat_message)` scrapes content text; failure raises AgentParsingError (feed-back-to-model class). The scrape slices from the FIRST `{` to the LAST `}` so surrounding prose is tolerated; JSONDecodeError position sniffing distinguishes the "two calls in one action" mistake (`},\n` at the failure point) from generic malformation, whose message quotes chars place−4..+5 for the model to self-correct. Arguments may arrive as a JSON-encoded STRING — `parse_json_if_needed` decodes dict-looking strings, else passes through. Synthetic ids are uuid4 because text protocols carry none.
**Invariant:** One-action-one-call is enforced by coaching, not schema: the model is told exactly why parsing failed. strict=False matters because models emit raw newlines inside strings; porters who enable strict mode convert a working scrape into spurious failures.
**Probe:** `tests/test_models.py::TestGetToolCallFromText.test_get_tool_call_from_text_basic/:_name_key_missing` (:917-935+), `tests/test_utils.py::test_parse_json_blob_with_invalid_json` (:484), agents-side `test_toolcalling_agent_api_misformatted_output` (:1891). Live: scrape `'Thought {"name":"w","arguments":"NY"} done'` → ChatMessageToolCall id=uuid, arguments="NY".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "parse_tool_calls get_tool_call_from_text parse_json_blob", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the first-brace-to-last-brace slice + positional error sniffing for any text-protocol tool format. Adapt key names via tool_name_key/tool_arguments_key per model family. Omit the multi-call coaching and weak models will loop forever on double calls.
