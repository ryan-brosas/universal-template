<!-- capsule-v2 -->
# Template tokenizer lexer — how do `{{...}}` blocks survive quotes, escapes, and garbage without corrupting surrounding text?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When scanning a prompt string for `{{...}}` blocks, when is `}}` inside a quoted value NOT a block terminator, and what happens to empty or unclosed fragments?

## Pair-scan state machine with quote-inert regions
**Path/Symbol:** `python/semantic_kernel/template_engine/template_tokenizer.py:TemplateTokenizer.tokenize` (28–107), `._extract_blocks` (110–161).
**Signature:** `def tokenize(text: str) -> list[Block]` (static); `def _extract_blocks(text, code_tokenizer, block_start_pos, end_of_last_block, next_char_pos) -> list[Block]`.
**Data Shape:** Input is the raw template string; output is an ordered list of TextBlock / VarBlock / ValBlock / CodeBlock. Empty/None text → `[TextBlock("")]`; any text shorter than 5 chars cannot contain a valid block → single TextBlock.

### Decisive source
```python
if not inside_text_value and current_char == Symbols.BLOCK_STARTER and next_char == Symbols.BLOCK_STARTER:
    block_start_pos = current_char_pos
    block_start_found = True
...
if inside_text_value:
    if current_char == Symbols.ESCAPE_CHAR and next_char in (Symbols.DBL_QUOTE, Symbols.SGL_QUOTE, Symbols.ESCAPE_CHAR):
        skip_next_char = True
        continue
    if current_char == text_value_delimiter:
        inside_text_value = False
    continue
```

**Flow:** Single left-to-right pass tracking four bits of state (`block_start_found`, `inside_text_value`, `text_value_delimiter`, `skip_next_char`). Inside a quoted value (started by `'` or `"`) the scanner ignores `{{`/`}}` entirely until the matching closing delimiter; `\` escapes only `"`, `'`, `\` by skipping the next char. On finding `}}` outside a value it calls `_extract_blocks`, which: emits a TextBlock for intervening text; returns the raw delimiters as a TextBlock if content is empty (`{{}}` → literal text); re-wraps `BlockSyntaxError` and `CodeBlockTokenError` from inner tokenizers as `TemplateSyntaxError` (warning-logged first). A block whose tokenized head is VALUE or VARIABLE is promoted out of CodeBlock form — `{{$a}}` yields a bare VarBlock, `{{'v'}}` a bare ValBlock.
**Invariant:** The lexer never raises on unterminated blocks — trailing text after the last complete block always becomes one final TextBlock, so malformed templates degrade to literal text rather than failing at tokenize time. Quote-inertness means `{{'{{a}}` tokenizes as ONE code block whose content contains a brace.
**Probe:** `python/tests/unit/template_engine/test_template_tokenizer.py::test_it_tokenizes_edge_cases_correctly_1` (107–123: `{{{{a}}` → [TEXT "{{", CODE "a"]); `::test_it_parses_text_without_code` matrix (10–32: `{{}}`, `{{ }}`, `{{  '}}x` all → single TEXT block); `::test_invalid_syntax` (81–104: `{{ plugin.func $va-r }}` → TemplateSyntaxError).
**Coverage caveat:** all cited paths checked via check_index_coverage — `no_recorded_issue` / `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "prompt template block code variable extract", limit: 10, fields: ["signature", "lines"] });
```
(Executed this pass: top hits = KernelPromptTemplate.extract_blocks, CodeBlock.render_code/parse_content/check_tokens, test matrices for both tokenizers.)

## Verdict
Adopt the quote-aware pair-scan with escape-only-quotes semantics and the promote-single-token rule (`{{$x}}` IS the variable, not a call). Adapt delimiter symbols to your host grammar. Omit nothing silently: preserve the degrade-to-text behavior for unclosed blocks — porters who instead raise on unterminated input break templates that embed literal braces.
