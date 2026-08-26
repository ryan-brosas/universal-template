<!-- capsule-v2 -->
# create_extract_graph_prompt token budget — first N-1 examples forced in, budget-checked only after min_examples_required

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how are few-shot examples packed into the extraction prompt under a hard token ceiling, and which examples are guaranteed to make it in?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/prompt_tune/generator/extract_graph_prompt.py`: `create_extract_graph_prompt` (:129-217).
**Signature:** `create_extract_graph_prompt(entity_types: str | list[str] | None, docs: list[str], examples: list[str], language: str, max_token_count: int, tokenizer=None, json_mode=False, output_path=None, min_examples_required=2) -> str`.
**Data Shape:** four template variants — typed/JSON vs untyped/plain selected by (`entity_types` presence, `json_mode`); examples rendered through `EXAMPLE_EXTRACTION_TEMPLATE` (or untyped twin) with 1-based numbering.

### Decisive source
```python
tokens_left = max_token_count - num_tokens(prompt) - num_tokens(entity_types)
for i, output in enumerate(examples):
    input = docs[i]                                  # zip-by-index: docs[i] ↔ examples[i]
    example_formatted = EXAMPLE_EXTRACTION_TEMPLATE.format(
        n=i + 1, input_text=input, entity_types=entity_types, output=output)
    example_tokens = tokenizer.num_tokens(example_formatted)
    if i >= min_examples_required and example_tokens > tokens_left:
        break                                        # first 2 ALWAYS included
    examples_prompt += example_formatted
    tokens_left -= example_tokens
prompt = prompt.format(entity_types=..., examples=examples_prompt, language=language)
```

**Flow:** pick template family → compute remaining budget after scaffold+types → iterate doc/example pairs, forcing at least `min_examples_required` (default 2) regardless of cost → keep appending while tokens remain → final `.format()` injects the accumulated examples block → optional write to `output_path/extract_graph.txt`.
**Invariant:** (1) The first `min_examples_required` examples bypass the budget check entirely — a prompt is guaranteed to teach the format even if every example is huge. (2) `docs` and `examples` are consumed by POSITION; mismatched lengths silently truncate to the shorter. (3) Budget accounting includes each example's full formatted text (numbering + types), not raw example text.
**Probe:** no direct unit file for create_extract_graph_prompt (CLI-level smoke coverage via `cli/prompt_tune.py` :25-114); pinned by whole-file read — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "create_extract_graph_prompt GRAPH_EXTRACTION_PROMPT min_examples_required tokens_left", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt minimum-guaranteed few-shot packing with tokenizer-exact accounting; adapt `min_examples_required` and template set to host; keep per-example FULL-format token measurement — measuring raw examples alone undercounts and overflows at runtime.
