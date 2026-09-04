<!-- capsule-v2 -->
# Structured-outputs internal mode — what changes when CodeAgent uses response_format instead of code-blob parsing?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** With `use_structured_outputs_internally=True`, which pipeline stages swap (prompt pack, response schema, parse path), and which providers even allow it?

## JSON-schema action contract
**Path/Symbol:** `src/smolagents/models.py:CODEAGENT_RESPONSE_FORMAT` (:43-67), `STRUCTURED_GENERATION_PROVIDERS=["cerebras","fireworks-ai"]` (:42); `agents.py` — template selection :1546-1554, request arg :1656-1658, parse branch :1704-1706; InferenceClientModel provider gate :1561-1565.
**Signature:** `use_structured_outputs_internally: bool = False`; response_format = json_schema {thought:string, code:string} required both, strict:True, name ThoughtAndCodeAnswer.
**Data Shape:** Model must return JSON with a "code" key; that value may itself be fenced (`extract_code_from_text(code_action, tags) or code_action` fallback).

### Decisive source
```python
# agents.py :1703-1709 — the parse fork:
if self._use_structured_outputs_internally:
    code_action = json.loads(output_text)["code"]
    code_action = extract_code_from_text(code_action, self.code_block_tags) or code_action
else:
    code_action = parse_code_blobs(output_text, self.code_block_tags)
code_action = fix_final_answer_code(code_action)
# models.py :1561-1563 — provider allowlist at the API boundary:
if response_format is not None and self.client_kwargs["provider"] not in STRUCTURED_GENERATION_PROVIDERS:
    raise ValueError("InferenceClientModel only supports structured outputs with these providers: cerebras, fireworks-ai")
```

**Flow:** Enabling the flag (a) swaps the default prompt pack to structured_code_agent.yaml, (b) adds `response_format=CODEAGENT_RESPONSE_FORMAT` to generate calls, and (c) REPLACES blob parsing with `json.loads → ["code"] → optional fence-strip`. Crucially the closing-tag auto-append (:1690-1695) is SKIPPED in this mode because history should stay raw JSON. Provider surface is heterogeneous: InferenceClientModel hard-gates to two providers; VLLM translates the OpenAI schema into StructuredOutputsParams; MLX/Transformers/Bedrock raise outright ("does not support structured outputs").
**Invariant:** The fence-strip fallback after json.loads exists because models wrap code in markdown INSIDE the JSON string field; assuming bare Python breaks on exactly the strongest instruction-followers. The stop-sequence carve-out and this mode interact: no closer-append means history normalization differs per mode.
**Probe:** `tests/test_agents.py::test_use_structured_outputs_internally` (:2364+). Live: flag-on agent with fake model returning '{"thought":"t","code":"final_answer(2)"}' → output 2 without any <code> tags.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "CODEAGENT_RESPONSE_FORMAT use_structured_outputs_internally", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-surface switch (prompts/request/parse) as one atomic feature flag. Adapt the schema fields to your action grammar. Omit the provider gate and unsupported backends fail mid-run instead of at init.
