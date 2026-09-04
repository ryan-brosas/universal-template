<!-- capsule-v2 -->
# F-string magic formatting — how does logfire.info(f"{x=}") recover both template AND values?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** How does the SDK reconstruct `{expr}` templates from an already-evaluated f-string at runtime, and what is the degradation ladder when introspection fails?

## ChunksFormatter._fstring_chunks + logfire_format_with_magic
**Path/Symbol:** `logfire/_internal/formatter.py:_fstring_chunks` (`formatter.py:61-150`) + `compile_formatted_value` (`formatter.py:278-314`) + fallback `logfire_format_with_magic` (`formatter.py:246-275`).
**Signature:** `chunks(format_string, kwargs, *, scrubber, fstring_frame: FrameType | None) -> tuple[list[Chunk], dict[str, Any], str]`.
**Data Shape:** returns (literal/arg chunks, extra_attrs keyed by EXPRESSION SOURCE text, new_template where each f-string value becomes `{source}`).

### Decisive source
```python
node_finder = FormattingCallNodeFinder(frame)   # executing-based AST node recovery
call_node = node_finder.node
if call_node is None:
    return None                                  # -> fall through to str.format path
...
if not isinstance(arg_node, ast.JoinedStr):
    return None                                  # not an f-string: normal formatting
...
source, value_code, formatted_code = compile_formatted_value(node_value, node_finder.source)
new_template += '{' + source + '}'               # rebuild the template from AST source
value = eval(value_code, global_vars, local_vars)
extra_attrs[source] = value                      # attribute named by SOURCE TEXT
formatted = eval(formatted_code, global_vars, {**local_vars, '@fvalue': value})
```
Template reconstruction deliberately avoids using raw f-string source: "We don't use the source code of the f-string because that gets messy if there's escaped quotes or implicit joining of adjacent strings." `compile_formatted_value` is `@lru_cache`d and pre-compiles TWO code objects: the expression itself, and a reformulated JoinedStr where the expression is replaced by Name `'@fvalue'` ('@ can't possibly conflict with a normal variable') so the format spec/conversion runs without re-evaluating the expression.
**Flow:** caller passes `inspect.currentframe().f_back` only when `config.inspect_arguments` → executing finds the Call node → arg located positionally (or `msg_template=` keyword for `.log`) → JoinedStr walk: Constants become literals, FormattedValues eval→stash→format→scrub via MessageValueCleaner → failure at ANY point raises KnownFormattingError/FStringAwaitError caught in `logfire_format_with_magic`, which warns with remediation text and degrades to `(format_string, {}, format_string)` — the span still ships.
**Flow (await):** `ast.walk` detects `ast.Await` BEFORE compiling and raises FStringAwaitError whose warning tells the user to pre-evaluate — await cannot work because the frame's values are post-await already.
**Invariant:** The message template stored on the span is rebuilt from normalized AST sources, never raw source text. Scrubbing of formatted values happens BEFORE truncation ("if 'password' is replaced by '...' because of truncation, that leaves '=123'"). `logfire.log` needs special arg detection (2nd positional or msg_template keyword).
**Probe:** `tests/test_formatter.py` (+ test_user_scripts/test_fstrings) — pins template reconstruction, `{x=}` handling, scrub-then-truncate order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "logfire_format_with_magic compile_formatted_value JoinedStr FormattingCallNodeFinder", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: AST-based template reconstruction, dual-code-object compilation with sentinel variable, structured degradation to raw string. Adapt requires the `executing` library or equivalent frame→AST mapping. Omit the `.log` positional quirk if your API lacks the twin entrypoint.
