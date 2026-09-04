<!-- capsule-v2 -->
# history typing — Why are assistant messages dict-ified before entering history, and why does it matter for porters?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What message representation does the loop standardize on and what breaks if a porter mixes pydantic objects into history?

## Plain dicts everywhere after one explicit conversion
**Path/Symbol:** `swarm/core.py:Swarm.run` (270-273).
**Signature:** `message.sender = active_agent.name; history.append(json.loads(message.model_dump_json()))`.
**Data Shape:** history entries: plain dicts with `role/content/sender/tool_calls` (tool_calls as list of dicts).

### Decisive source
```python
message = completion.choices[0].message
debug_print(debug, "Received completion:", message)
message.sender = active_agent.name
history.append(
    json.loads(message.model_dump_json())
)  # to avoid OpenAI types (?)
```

**Flow:** SDK pydantic message → stamp non-standard `sender` field → round-trip through `model_dump_json`/`json.loads` → plain dict appended. Tool messages are built as dicts directly in `handle_tool_calls`.
**Invariant:** The `sender` attribute exists only because Swarm adds it — it is NOT part of the OpenAI schema, which is exactly why serialization to dict is required to keep it in history (and why streaming pops it back out per delta). Uniform dict history means consumers (REPL pretty-printer, examples) index with `[...]`, never attribute access. The inline comment "to avoid OpenAI types (?)" records the authors' own uncertainty — treat dict-ification as a deliberate boundary, not an accident.
**Probe:** `tests/test_core.py:test_run_with_simple_message` asserts `response.messages[-1]["role"] == "assistant"` — subscript access on a dict pins the representation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "Swarm class run method completion tool calls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one explicit serialization boundary at history ingress so downstream code can assume dicts. Adapt the mechanism (`model_dump_json` → your serializer). Omit the sender-stamping hack if your schema has a native speaker field — but keep SOME per-message speaker attribution, since multi-agent replay depends on it.
