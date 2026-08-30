<!-- capsule-v2 -->
# OpenAI structured-LLM parse endpoint — why beta.chat.completions.parse and what params survive the reasoning gate?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does the structured-output LLM twin differ from the plain OpenAI twin, and which parameters reach the wire?

## Connected graph-selected seam
**Path/Symbol:** `mem0/llms/openai_structured.py`: `OpenAIStructuredLLM.generate_response` (:21-49); param gate inherited from `mem0/llms/base.py::_get_supported_params` (:96-129); factory registration `mem0/utils/factory.py:50` ("openai_structured" → OpenAIStructuredLLM, OpenAIConfig).
**Signature:** `generate_response(messages, response_format=None, tools=None, tool_choice="auto") -> str`.
**Data Shape:** default model `gpt-5-mini`; response_format forwarded verbatim (pydantic class or JSON-schema dict per SDK contract); returns `.choices[0].message.content` string.

### Decisive source
```python
params = self._get_supported_params(messages=messages)   # reasoning gate from LLMBase
params["model"] = self.config.model
if response_format:
    params["response_format"] = response_format
if tools:
    params["tools"] = tools
    params["tool_choice"] = tool_choice
response = self.client.beta.chat.completions.parse(**params)
return response.choices[0].message.content
```

**Flow:** base-class gate first — for reasoning-family models (o1/o3/GPT-5 allowlist) ONLY messages/response_format/tools/tool_choice plus optional reasoning_effort pass; sampling params (temperature/top_p) and max_tokens are stripped at the gate, not here → model + optional format/tools merged → call goes to the SDK's **beta parse endpoint**, which parses structured output server-side into typed objects — the defining difference from the plain twin's `chat.completions.create` → content extracted as plain string.
**Invariant:** the reasoning-model parameter whitelist lives in ONE place (`llms/base.py`, shared with every LLM twin via inheritance — see llm-base-param-gate capsule) and this file adds only endpoint choice + passthrough fields; a porter who re-implements filtering locally diverges from the fleet-wide table on the next model-name addition. api_key/base_url resolve config-first then env (`OPENAI_API_KEY`/`OPENAI_BASE_URL`) with the api.openai.com default.
**Probe:** `grep -n "beta.chat.completions.parse" mem0/llms/openai_structured.py` (exactly :48).
**Direct test:** no dedicated unit suite for this 49-line twin at this pin; the shared gate it consumes is exercised by tests/llms/* suites for sibling providers. Coverage caveat recorded (thin-file ruling).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "OpenAIStructuredLLM generate_response beta chat completions parse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-gate + thin-endpoint-twin shape (structured output = same params, different SDK method) for any provider offering a parse/JSON-mode endpoint; adapt default model/env names; omit local re-filtering of params. Thin-file direct-test caveat recorded.
