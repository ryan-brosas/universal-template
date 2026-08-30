<!-- capsule-v2 -->
# CodeBlock positional arity contract — which token positions may hold what, and when do extra tokens get silently dropped?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** A code block is a function call plus arguments — what is the exact positional grammar, and where does validation happen (construction or render)?

## Pydantic-validated token positions
**Path/Symbol:** `python/semantic_kernel/template_engine/blocks/code_block.py:CodeBlock.parse_content` (56–65), `.check_tokens` (68–103).
**Signature:** `@model_validator(mode="before") parse_content(fields)`; `@field_validator("tokens", mode="after") check_tokens(tokens) -> list[Block]`.
**Data Shape:** `tokens: list[Block]` with `type: ClassVar[BlockTypes] = BlockTypes.CODE`. Construction accepts either `content=` (tokenized fresh via CodeTokenizer) or pre-built `tokens=` (parse skipped).

### Decisive source
```python
if not tokens:
    raise CodeBlockTokenError("The content should contain at least one token.")
for index, token in enumerate(tokens):
    if index == 0 and token.type == BlockTypes.NAMED_ARG:
        raise CodeBlockTokenError(...)          # cannot start with named arg
    if index == 0 and token.type in [BlockTypes.VALUE, BlockTypes.VARIABLE]:
        if len(tokens) > 1:
            logger.warning("... more tokens ... will be ignored.")
        return [token]                          # collapses to lone value/var
    if index == 1 and token.type not in VALID_ARG_TYPES:   # value | variable | named_arg
        raise CodeBlockTokenError(...)
    if index > 1 and token.type != BlockTypes.NAMED_ARG:
        raise CodeBlockTokenError(...)          # everything after slot 1 is named-only
```

**Flow:** Validation fires at pydantic construction time (import/template-parse), never at render. The grammar is: `[function_id] [value|variable|named_arg] named_arg*`. A leading VALUE/VARIABLE makes the block a pure substitution — all following tokens are discarded with only a warning, so `{{$a extra}}` silently equals `{{$a}}`. A leading NAMED_ARG is always an error; a second FUNCTION_ID (e.g. `func other.func`) is an error at index 1.
**Invariant:** The collapse rule means arity errors can NEVER be detected for value/var-led blocks — porters relying on CodeBlock to surface "too many arguments" for non-function blocks will get silent truncation instead. Empty token lists raise even when the caller explicitly passes `tokens=[]`.
**Probe:** `python/tests/unit/template_engine/blocks/test_code_block.py::test_positional_validation` (344–461, triple-parametrized matrix pinning every valid/invalid combination incl. `arg1=$arg1` as invalid token0); `::test_block_validation` (331–384, syntax-error union); `::test_no_tokens` (483–485).
**Coverage caveat:** cited paths checked via check_index_coverage — clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "check_tokens CodeBlockTokenError first token function_id second named arg", limit: 8, fields: ["signature", "lines"] });
```
(Executed this pass.)

## Verdict
Adopt the three-slot grammar and construction-time validation so template authors fail fast. Adapt VALID_ARG_TYPES membership if your host adds block kinds. Omit nothing: keep the warning-and-collapse behavior for value/var-led blocks verbatim — changing it to an error breaks templates that append annotations after a variable.
