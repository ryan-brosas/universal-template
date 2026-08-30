<!-- capsule-v2 -->
# Code tokenizer grammar — what makes a legal token inside `{{ }}`, and when is a function-id actually a named argument?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How are the space-separated tokens inside one code block classified, and which malformed inputs fail at tokenization vs at block validation?

## First-char dispatch with mandatory space separators
**Path/Symbol:** `python/semantic_kernel/template_engine/code_tokenizer.py:CodeTokenizer.tokenize` (29–157).
**Signature:** `def tokenize(text: str) -> list[Block]` (static).
**Data Shape:** Output tokens are FunctionIdBlock / VarBlock / ValBlock / NamedArgBlock. Empty/whitespace input → `[]`; single non-space char → `[FunctionIdBlock]` unconditionally.

### Decisive source
```python
if index == 0:
    if current_char == Symbols.VAR_PREFIX:
        current_token_type = BlockTypes.VARIABLE
    elif current_char in (Symbols.DBL_QUOTE, Symbols.SGL_QUOTE):
        current_token_type = BlockTypes.VALUE; text_value_delimiter = current_char
    else:
        current_token_type = BlockTypes.FUNCTION_ID
...
if current_token_type == BlockTypes.FUNCTION_ID:
    if Symbols.NAMED_ARG_BLOCK_SEPARATOR.value in current_token_content:
        blocks.append(NamedArgBlock(content="".join(current_token_content)))
    else:
        blocks.append(FunctionIdBlock(content="".join(current_token_content)))
```

**Flow:** Tokens accumulate until whitespace (space/newline/CR/tab) closes them — only VARIABLE and FUNCTION_ID get flushed at the separator; VALUE flushes at its closing quote. A new token after a separator re-dispatches on its first character. Two failure points raise `CodeBlockSyntaxError("Tokens must be separated by one space least")`: mid-loop when a fresh token starts without a preceding separator, and the last-token `else` branch when trailing characters follow an unclosed construct. The key subtlety: **named-arg classification happens in the tokenizer** — any FUNCTION_ID-typed chunk whose content contains `=` is emitted as NamedArgBlock, which later re-validates itself against `NAMED_ARG_REGEX` (`name=($var|'quoted')`) and raises NamedArgBlockSyntaxError on mismatch.
**Invariant:** Escaping (`\` before `"`, `'`, `\`) applies ONLY inside quoted values; variable names are `[0-9A-Za-z_]+` (no dots, no hyphens) while function ids allow dots (`plugin.function`). Token boundaries are whitespace-only — there is no operator grammar.
**Probe:** `python/tests/unit/template_engine/test_code_tokenizer.py::test_it_supports_escaping` (103–109: `func 'f\'oo'` → content `'f'oo'`); `::test_it_throws_when_separators_are_missing` (112–120); `::test_named_args` (123–130: 4-token split incl. `arg2="arg2"`).
**Coverage caveat:** all cited paths checked via check_index_coverage — clean. (.NET `CodeTokenizer.cs` twin appeared in retrieval but is out of leaf scope.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "CodeTokenizer tokenize var val function id named arg blocks", limit: 8, fields: ["signature", "lines"] });
```
(Executed this pass.)

## Verdict
Adopt the first-char dispatch + mandatory-separator grammar and the "contains `=` ⇒ named arg" heuristic with downstream regex re-validation. Adapt the symbol set ($ prefix, quote chars) to your host. Omit the C# twin's longer state machine — port from the Python form; keep the two-stage error timing (tokenizer raises syntax errors, block validator raises arity errors) because tests pin both separately.
