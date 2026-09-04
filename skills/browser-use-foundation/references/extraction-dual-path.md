<!-- capsule-v2 -->
# Dual-path structured/free-text extraction — how does one action serve schema-bound and ad-hoc data extraction with identical truncation semantics?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does the extract action turn an optional JSON Schema into a validated pydantic payload while gracefully falling back to free text?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `extract` action (:1096-1315): MAX_CHAR_LIMIT=100_000 (:1108), image-keyword auto-enable (:1121), `schema_dict_to_pydantic_model` fallback (:1131), structured branch (:1177-1219), free-text branch (:1224-1315).
**Signature:** `async def extract(params: ExtractAction, browser_session, page_extraction_llm: BaseChatModel, file_system: FileSystem, extraction_schema: dict | None = None)`.

### Decisive source
```python
# Schema admission is TRY-then-DOWNGRADE, never fail:
structured_model = None
if output_schema is not None:
    try:
        from browser_use.tools.extraction.schema_utils import schema_dict_to_pydantic_model
        structured_model = schema_dict_to_pydantic_model(output_schema)
    except (ValueError, TypeError) as exc:
        logger.warning(f'Invalid output_schema, falling back to free-text extraction: {exc}')
        output_schema = None

# Both paths share: asyncio.wait_for(..., timeout=120.0) around the LLM call,
# <url><query><result> envelope, and the SAME overflow contract:
MAX_MEMORY_LENGTH = 10000
if len(extracted_content) < MAX_MEMORY_LENGTH:
    memory = extracted_content; include_extracted_content_only_once = False
else:
    file_name = await file_system.save_extracted_content(extracted_content)
    memory = f'Query: {query}\nContent in {file_name} and once in <read_state>.'
    include_extracted_content_only_once = True
```

**Flow:** params accepted as pydantic model OR dict (defensive dual access) → query keywords ('image', 'photo', 'thumbnail'...) auto-enable `extract_images` → markdown via unified extractor + structure-aware chunking (see markdown-structure-chunking) with `overlap_prefix` prepended → structured path invokes LLM with `output_format=structured_model`, dumps pydantic to JSON inside `<structured_result>` tags plus an `ExtractionResult` metadata blob (`is_partial=truncated`); free-text path prompts with anti-hallucination instructions and `<already_collected>` dedupe list (capped at 100 items) → both paths write >10k results to FileSystem files and point memory at them.
**Invariant:** invalid schemas must downgrade to free-text, never raise; the 120s inner LLM cap is what the outer 180s action guard budgets for; `already_collected` identifiers are advisory skip-lists for cross-page pagination dedupe, enforced by prompt instruction not post-filter.
**Probe:** `tests/ci/test_structured_extraction.py` (schema_utils matrix: nested/array-of-primitives/enum/optional-null defaults :29-152), `tests/ci/test_extract_images.py`, coverage caveat: live-LLM branches exercised only in e2e.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "extract output_schema schema_dict_to_pydantic_model already_collected save_extracted_content", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt try-then-downgrade schema admission + shared 120s/overflow contracts + already_collected prompt dedupe; adapt prompt copy; omit ExtractionResult metadata if you lack a metadata channel.
