<!-- capsule-v2 -->
# GLiNER2 specialist delegation — how do you route ONE operation to a small local model while everything else flows to the general LLM?

**Source:** Graphiti Apache-2.0 `main@401c59a` (`graphiti_core/llm_client/gliner2_client.py`); Codebase Memory `graphiti`. **Question:** What is the correct wrapper shape for a cheap NER-specialist that handles a single response_model and transparently delegates the rest — without corrupting either path's contract?

## Response-model-name dispatch + prompt-scraping label extraction + sync-load warning
**Path/Symbol:** `graphiti_core/llm_client/gliner2_client.py:GLiNER2Client.generate_response` (:253–328), `_is_gliner2_operation` (:217–221), `_extract_entity_labels` (:140–172), `_extract_text_from_messages` (:120–138), `_handle_entity_extraction` (:176–213), ctor (:66–108).
**Signature:** `async generate_response(self, messages: list[Message], response_model: type[BaseModel] | None = None, ..., *, attribute_extraction: bool = False) -> dict`; `__init__(..., llm_client: LLMClient | None = None)` raises ValueError when no delegate is supplied.
**Data Shape:** dispatch key = `response_model.__name__ == 'ExtractedEntities'` (string compare, not isinstance); output `{'extracted_entities': [{'name': str, 'entity_type_id': int}]}`; labels scraped from `<ENTITY TYPES>` blocks; text from `<CURRENT MESSAGE>`/`<TEXT>`/`<JSON>` tags with full-content fallback.

### Decisive source
```python
# Prompt templates interpolate Python list[dict] directly,
# producing Python repr (single quotes, None) rather than JSON.
try:
    entity_types = json.loads(raw)
except json.JSONDecodeError:
    entity_types = ast.literal_eval(raw)
```
and the delegation gate:
```python
if not self._is_gliner2_operation(response_model):
    return await self.llm_client.generate_response(
        messages,
        response_model=response_model,
        max_tokens=max_tokens,
        ...
        attribute_extraction=attribute_extraction,
    )
```
plus the ctor note:
```
Note: When using local models (no base_url), initialization loads model
weights synchronously. Create this client before entering the async
event loop (e.g., before ``asyncio.run()``).
```

**Flow:** every call hits the name gate FIRST — only `ExtractedEntities` stays local, ALL other operations (dedup, summarization, edge extraction) forward untouched to the wrapped `llm_client`, including the keyword-only attrs flag. Local path: clean input → scrape `<ENTITY TYPES>` from the LAST message via json-then-ast.literal_eval ladder (prompt templates interpolate Python repr, not JSON) → run GLiNER2 in a worker thread (`asyncio.to_thread`) so CPU-bound inference doesn't stall the loop → map results back through `label_to_id` (unknown types default id 0), skipping empty names → approximate token accounting (`len//4`) into the shared tracker → cache read/write like any other client. Failure mapping: 'rate limit'/'429' substrings → RateLimitError; auth errors re-raised bare.
**Invariant:** the specialist NEVER fabricates non-native responses — if it can't parse labels it degrades to `{'Entity': 'General entity'}` and still returns entity-shaped dicts; the delegate receives byte-identical arguments so behavior for delegated ops is indistinguishable from using the inner client alone. Sync weight-loading must happen BEFORE the event loop starts (documented ctor constraint).
**Probe:** coverage caveat — no direct test suite upstream (`tests/llm_client/` covers token-tracker + openai-client only). Deterministic probes: feed a Python-repr `<ENTITY TYPES>` block and assert ast-ladder parses what json.loads rejects; assert a None response_model delegates.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "GLiNER2Client _is_gliner2_operation _extract_entity_labels", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the one-operation-specialist wrapper (name-gate + full-fidelity delegation + to_thread offload + graceful label degradation). Adapt the tag-scraping to your own prompt grammar — better, emit structured fields beside the tags so scraping dies. Omit the len//4 token estimate where real usage numbers exist. This is graphiti's cost-tier pattern (small local model for high-volume extraction, big API model for reasoning) made concrete.
