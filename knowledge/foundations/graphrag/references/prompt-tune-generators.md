<!-- capsule-v2 -->
# prompt-tune generator chain — persona→entity_types pipeline where json_mode returns parsed list and plain mode returns raw text

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how are domain, persona, language, and entity types bootstrapped for prompt tuning, and what does each step return in json vs plain mode?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/prompt_tune/generator/`: `persona.py::generate_persona` (:55-73), `domain.py::generate_domain` (:88-107), `language.py::detect_language` (:122-141), `entity_types.py::generate_entity_types` (:171-215) + `EntityTypesResponse` (:165-168); `cli/prompt_tune.py`: orchestration (:25-114).
**Signature:** `generate_entity_types(model, domain: str, persona: str, docs, task=DEFAULT_TASK, json_mode=False) -> str | list[str]`.
**Data Shape:** `DEFAULT_TASK` carries a `{domain}` slot every caller must `.format(domain=...)`; persona rides as the SYSTEM message while generated prompts ride as USER messages; `EntityTypesResponse{entity_types: list[str]}` is the pydantic response_format in JSON mode.

### Decisive source
```python
formatted_task = task.format(domain=domain)          # DEFAULT_TASK has {domain} baked in
messages = (CompletionMessagesBuilder()
            .add_system_message(persona)             # persona = system, not inline text
            .add_user_message(entity_types_prompt).build())
if json_mode:
    response = await model.completion_async(messages=messages,
                                            response_format=EntityTypesResponse)
    parsed_model = response.formatted_response
    return parsed_model.entity_types if parsed_model else []   # parse-fail → EMPTY LIST
return (await model.completion_async(messages=messages)).content  # raw string otherwise
```

**Flow:** CLI order is docs → (`--domain` flag or `generate_domain`) → `detect_language` (unless `--language` given) → `generate_persona` → `generate_entity_types(persona as system)` → `create_extract_graph_prompt` / community-report / entity-summarization prompts written to the output dir. Each generator is one completion call with no retry/parse ladder beyond the json-mode None guard.
**Invariant:** (1) The task string ALWAYS flows through `.format(domain=...)` — passing a task containing other braces crashes `.format`, which is why doc chunks were brace-escaped upstream. (2) json vs plain changes the RETURN TYPE (list[str] vs str) — callers branch on mode. (3) Persona enters via system role; generators never concatenate it into user text.
**Probe:** no direct unit files for the four generators (CLI smoke coverage only; loader side has `tests/unit/prompt_tune/test_load_docs_in_chunks.py`); pinned by whole-file reads — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "generate_persona generate_domain detect_language generate_entity_types EntityTypesResponse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bootstrap chain (domain → language → persona-as-system → typed entity list) with dual-mode return contracts; adapt prompts/personas per host domain; keep the `{domain}`-format discipline paired with upstream brace escaping — they only work together.
