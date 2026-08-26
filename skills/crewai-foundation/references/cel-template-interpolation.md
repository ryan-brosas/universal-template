<!-- capsule-v2 -->
# CEL template interpolation — how do `${...}` expressions inside declarative strings read flow state while keeping literal text and value types intact?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What is the segment-parse/eval contract that makes `"Ticket: ${state.ticket_id}"` work without turning everything into strings?

## Lexer-driven brace matching + typed single-expression passthrough
**Path/Symbol:** `lib/crewai/src/crewai/flow/expressions.py` (`_marker_end` :56–74, `_parse_template_segments` :77–92 lru_cached, `FLOW_TEMPLATE_EXPRESSION_RULES` :95–113).
**Signature:** `_parse_template_segments(value: str) -> tuple[str | _ExpressionSegment, ...]` (cached, maxsize=256).
**Data Shape:** segments = literal strings OR `_ExpressionSegment(source)`; rules: `state.*` for input data, `outputs.step_name` for completed method results.

### Decisive source
```python
def _marker_end(value: str, start: int) -> int:
    from celpy.celparser import CELParser
    CELParser()
    parser: Any = CELParser.CEL_PARSER
    depth = 1
    try:
        for token in parser.lex(value[start:]):
            if token.type == "LBRACE":
                depth += 1
            elif token.type == "RBRACE":
                depth -= 1
                if depth == 0:
                    return start + int(token.start_pos)
    except Exception as e:
        raise ExpressionError(
            f"unterminated or invalid ${{...}} expression in {value!r}: {e}"
        ) from e
    raise ExpressionError(f"unterminated ${{...}} expression in {value!r}")
```
```python
# shipped authoring rules (FLOW_TEMPLATE_EXPRESSION_RULES)
"If a value is only one `${...}` expression, the result keeps its type. "
"Use this for numbers, booleans, objects, and lists.",
"In action mapping strings, keep literal text outside `${...}` ... "
"do not assemble the string with CEL `+`."
```

**Flow:** template split into cached segments → closing brace found by LEXING (not regex) so nested braces/dicts inside expressions parse correctly; unterminated ⇒ ExpressionError naming the original value → whole-string single expression keeps native type; mixed text coerces non-text values to JSON with null→empty-text.
**Invariant:** Brace depth counting must use the CEL lexer — a naive `%}`-style splitter mis-closes on `${state.map({"a": 1})}`. The cache is keyed by raw string so hot loops re-parse nothing. The rules block is itself shipped to LLMs as authoring guidance (single source of truth for the grammar's intent).
**Probe:** static anchors at pin: `grep -c "_CEL_MACROS_WITH_LOCAL_BINDINGS" lib/crewai/src/crewai/flow/expressions.py` → 2; `_parse_template_segments` lru_cache line :76–77. Coverage caveat: no upstream unit test isolates `_marker_end` — pinned via definition-level expression tests + source inspection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "CEL expression template segments marker_end state outputs interpolation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lexer-based delimiter matching + type-preserving single-expression rule; adapt the CEL dependency (swappable with any expression lang keeping the two-phase contract); omit macro local-binding support if you ban filter/map in user templates.
