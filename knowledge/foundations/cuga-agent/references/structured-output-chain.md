<!-- capsule-v2 -->
# Structured-output chain factory — how to build a validated, provider-dialect-aware structured-output LLM chain

**Source:** cuga-agent (Apache-2.0) `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do I build a `prompt | llm` chain that returns a validated Pydantic object and still works when the endpoint silently ignores OpenAI's structured-output spec?

## Provider-dialect chain factory
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/shared/base_agent.py:BaseAgent.get_chain` (204-277), `BaseAgent.create_validated_structured_output_chain` (129-176), `BaseAgent.get_format_instructions` (179-201).
**Signature:** `BaseAgent.get_chain(prompt_template, llm, schema=None, wx_json_mode='response_format') -> Runnable`; `create_validated_structured_output_chain(llm, schema, prompt_template=None) -> Runnable`.
**Data Shape:** input = prompt variables dict; output = a validated Pydantic instance of `schema` (or a raw `AIMessage` when `schema is None` / `wx_json_mode=='no_format'`). Failure shape: transport/auth/rate-limit errors propagate; only *schema-ignored* failures fall back.

### Decisive source
```python
def _json_schema_unusable(exc):
    # Endpoint ignored the schema => retrying identical request can't help.
    return (_structured_output_missing_parsed_field(exc)
            or isinstance(exc, (ValidationError, OutputParserException))
            or isinstance(exc, json.JSONDecodeError))

def create_validated_structured_output_chain(llm, schema, prompt_template=None):
    json_schema_chain = prompt_template | llm.with_structured_output(schema, method="json_schema")
    parser = PydanticOutputParser(pydantic_object=schema)
    # The fallback runs the model UNCONSTRAINED, so the prompt must carry the
    # shape itself — a bare parser only validates, never asks for JSON.
    json_mode_prompt = (prompt_template + ChatPromptTemplate.from_messages(
        [("system", "{cuga_format_instructions}")])).partial(
        cuga_format_instructions=BaseAgent.get_format_instructions(parser))
    json_mode_chain = json_mode_prompt | llm | parser
    async def _invoke_with_fallback(inputs):
        try:
            return BaseAgent.validate_and_retry_output(await json_schema_chain.ainvoke(inputs), schema)
        except Exception as exc:
            if _json_schema_unusable(exc):
                return BaseAgent.validate_and_retry_output(await json_mode_chain.ainvoke(inputs), schema)
            raise   # auth/rate-limit/connection must propagate for the caller's retry
    return RunnableLambda(_invoke_with_fallback).with_retry(stop_after_attempt=3)
```

**Flow:** `get_chain` dispatches by provider type — ChatWatsonx (with `$defs`-schema guided-decoding fallback to prompt-parser, `function_calling`/`json_mode` methods), ChatOpenAI whose model name contains `claude`/`gcp` (skip native json_schema → `prompt | llm | parser` to avoid Bedrock `output_config` 400), ChatLiteLLM (plain parser), ChatOpenAI/ChatGroq (the validated fallback chain), else `with_structured_output(method="json_schema")`. Every branch ends `.with_retry(stop_after_attempt=3)`.
**Invariant:** A schema-ignored endpoint falls back exactly once to json_mode (no retry storm on the identical failing request); a real transport error must NOT be swallowed into a json_mode call — it propagates so the caller's retry can do its job (#639).
**Probe:** `tests/unit/test_structured_output_fallback.py::test_production_chain_falls_back_and_carries_format_instructions` (drives the real chain; asserts call order `["json_schema(json_schema)", "json_mode"]` and that the fallback prompt carries the schema), `::test_production_chain_does_not_fall_back_on_transport_error` (ConnectionError propagates, json_mode never called), `::test_schema_ignored_by_endpoint_triggers_fallback` / `::test_transport_errors_still_propagate` (the `_json_schema_unusable` classifier); `tests/unit/test_base_agent_claude_json_schema.py::test_chat_openai_skips_native_json_schema` (Claude/Bedrock skip matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "BaseAgent get_chain create_validated_structured_output_chain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `json_schema`→`json_mode` fallback keyed on `_json_schema_unusable` (only schema-ignored failures fall back; transport errors propagate), the format-instructions-in-prompt partial so the unconstrained fallback still emits schema-shaped JSON, and the per-provider dialect dispatch (watsonx `$defs` guided-decoding, Claude/Bedrock skip, LiteLLM parser). Adapt the model-name sniffing (`_chat_openai_model_name`) and the watsonx schema swap (`APIPlannerOutputWX`) to your provider set. Omit the hard-coded `APIPlannerOutput*` schema references. Coverage: all cited source/test paths `no_recorded_issue` + `metadata_match` on the live full index.
