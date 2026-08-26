<!-- capsule-v2 -->
# Flow B Model-Then-Human Extraction Dispatch — how do you run document extraction across LLM and OCR providers without leaking customer keys or documents?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How does one dispatch layer serve single-call LLM providers AND two-step OCR providers while keeping every vendor call on the customer's machine?

## One dispatcher, two provider flavors, local-only execution
**Path/Symbol:** `packages/python/awaithumans/awaitverify/extraction.py` — module docstring (:1–19 states the trust contract), `run_extraction` (:103–158 isinstance ladder), `_extract_openai` (:164), `_run_openai_responses_extract` (:265), `_extract_azure_openai` (:311), `_extract_reducto` (:405), `_extract_azure_di` (:533), `_extract_anthropic` (:631), `run_structuring` (:748), `_structure_azure_openai_text_only` (:819); direct test `packages/python/tests/awaitverify/test_extraction_smoke.py`.
**Signature:** `run_extraction(*, document_bytes: bytes, extraction: ExtractionConfig, response_schema: type[BaseModel], client: AwaitHumans) -> dict[str, Any]`; `run_structuring(*, raw_extraction: str, structuring: StructuringConfig, response_schema, client) -> dict[str, Any]`.
**Data Shape:** every branch returns a plain dict already validated against `response_schema`; errors are typed (`ExtractionFailedError` code `EXTRACTION_FAILED`, `ProviderNotSupportedError` code `PROVIDER_NOT_SUPPORTED_YET`, credential ladders raise `VerifyError` with actionable codes like `EXTRACTION_API_KEY_MISSING`).

### Decisive source
```python
# run_extraction — isinstance dispatch, NOT a registry: order is irrelevant
# because config classes are disjoint, and unimplemented providers fail LOUD:
if isinstance(extraction, DoclingExtraction):
    raise ProviderNotSupportedError("DoclingExtraction")   # typed config exists, API call doesn't
raise ProviderNotSupportedError(type(extraction).__name__)

# _run_openai_responses_extract :265-308 — strict mode deliberately OFF:
response = await sdk.responses.create(
    model=model,
    input=[{"role": "user", "content": content}],
    text={"format": {"type": "json_schema", "name": "verify_document_extraction",
                     "schema": response_schema.model_json_schema(), "strict": False}},
)
raw = response.output_text or ""
try:
    parsed = json.loads(raw)
except json.JSONDecodeError as exc:
    raise ExtractionFailedError(provider_label, f"non-JSON content: {raw[:200]}") from exc
try:
    response_schema.model_validate(parsed)          # server-side enforcement instead
except Exception as exc:
    raise ExtractionFailedError(provider_label, str(exc)) from exc
```

**Flow:** Responses-API choice is load-bearing: both OpenAI-direct and Azure use `sdk.responses.create` with `text.format=json_schema` because chat.completions REJECTS `response_format` on GPT-5.x ("Unsupported parameter… has moved to text.format" — pinned in both docstrings). Anthropic gets structured output via a forced tool call (`tool_choice={"type":"tool","name":"submit_extraction"}` + scan for the `tool_use` block). Reducto is two HTTP calls (upload → `/extract` with schema inside `instructions`). Azure DI is OCR→Markdown then delegates to `run_structuring`, which rebuilds an `OpenAIExtraction`/`AzureOpenAIExtraction`-shaped proxy so the TEXT-ONLY structuring call reuses the same credential resolver and the same `_run_openai_responses_extract` core.
**Invariant:** (1) ALL model calls execute on the caller's machine — only the structured result ever reaches the server; vendors receive the document only when the customer chose them (Reducto/Azure DI exception stated in docstrings). (2) Credentials resolve per-field: extraction-config value OVERRIDES client-level bundle; missing → typed error whose hint shows BOTH setup places verbatim. (3) `strict: False` is deliberate — customer Pydantic schemas commonly carry Optionals that OpenAI strict mode rejects; validation happens via `model_validate` after parse. (4) Vendor SDKs are lazy imports raising `VerifyDepsMissingError("<extra>")` — the base package never hard-depends on openai/anthropic/reducto/azure. (5) Unimplemented-but-typed providers (Docling, PaddleOCR, AnthropicStructuring) must raise `ProviderNotSupportedError`, never silently fall through.
**Probe:** `packages/python/tests/awaitverify/test_extraction_smoke.py` — offline contract tests `test_docling_extraction_raises_not_supported` (:197), `test_paddleocr_extraction_raises_not_supported` (:208), `test_anthropic_structuring_raises_not_supported` (:217) pin invariant 5 without network; vendor smoke tests (:104+) are env-gated and skipped in CI by design ("cost real tokens"). Coverage caveat: no offline test drives `_run_openai_responses_extract` itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "run_extraction run_structuring ProviderNotSupportedError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-flavor dispatch + loud ProviderNotSupportedError for typed-but-unimplemented configs, the Responses-API-not-chat.completions choice, forced-tool-call structured output for Anthropic, strict-off + post-parse model_validate, lazy vendor imports, and the override-ladder credential resolution verbatim. Adapt provider sets to your vendors. Omit nothing — the trust contract ("keys and documents stay local") is the product boundary this file enforces.
