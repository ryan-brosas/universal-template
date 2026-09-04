<!-- capsule-v2 -->
# Tool inputs-schema synthesis without pydantic — how does get_json_schema turn docstring + hints into the OpenAI tool envelope?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory project `smolagents`. **Question:** How does smolagents build the `inputs` JSON Schema for `@tool` functions using only `inspect` + regexes, and what does it hard-require from the author?

## Path/Symbol
- `src/smolagents/_function_type_hints_utils.py:get_json_schema` (:97-231), `_parse_google_format_docstring` (:256-288), section regexes :234-253.
- Consumer: `src/smolagents/tools.py:tool` (:1061-1068).

## Signature
`get_json_schema(func: Callable) -> dict` → `{"type": "function", "function": {"name", "description", "parameters": {"type":"object","properties","required"}, ["return"]}}`.

## Data Shape
Docstring contract: Google format REQUIRED. Main text = description; every parameter MUST have an `Args:` entry or `DocstringParsingException` (:196-200); `Returns:` optional ("most chat templates ignore the return value"); trailing `(choices: ["a","b"])` on an arg description becomes `enum` and is stripped from the text (:202-206).

### Decisive source
```python
# _function_type_hints_utils.py:234-237 — section extraction regexes
description_re = re.compile(r"^(.*?)(?=\n\s*(Args:|Returns:|Raises:)|\Z)", re.DOTALL)
args_re       = re.compile(r"\n\s*Args:\n\s*(.*?)[\n\s]*(Returns:|Raises:|\Z)", re.DOTALL)
# :202-206 — choices suffix → enum, removed from description
enum_choices = re.search(r"\(choices:\s*(.*?)\)\s*$", desc, flags=re.IGNORECASE)
if enum_choices:
    schema["enum"] = [c.strip() for c in json.loads(enum_choices.group(1))]
    desc = enum_choices.string[: enum_choices.start()].strip()
# :231 — OpenAI wire envelope
return {"type": "function", "function": output}
```

## Flow
`inspect.getdoc` → strip → `_parse_google_format_docstring` (blank lines dropped, multi-line descriptions re-joined with single spaces via `re.sub(r"\s*\n+\s*", " ")`) runs BESIDE `_convert_type_hints_to_json_schema(func)` (types come only from hints — docstring types are ignored, see vocabulary capsule); the synthesized `"return"` property is popped out of `parameters.properties` and attached as top-level `function.return` with the Returns-doc attached if present. `tools.tool` then consumes `[\"function\"]` and REQUIRES a return type hint: missing return property raises `TypeHintParsingException` UNLESS the function has zero parameters, in which case it injects `{"return": {"type": "null"}}` (tools.py:1062-1068).

## Invariant
Types never come from the docstring; descriptions always do. A function whose docstring lacks any one argument description is unusable at import time of the tool (`@tool` decoration fails), not at call time. The output is exactly the OpenAI function-tool envelope so it can be handed to chat templates verbatim.

## Probe
`tests/test_function_type_hints_utils.py::TestGetJsonSchema.test_get_json_schema_example` (:241-271) asserts the full expected dict incl. `"required": ["x"]` and tuple|None prefixItems+nullable; `.test_get_json_schema_raises` (:289-301) pins `DocstringParsingException` for missing docstring AND missing arg docs; `tests/test_tools.py::TestTool.test_tool_init_decorator_raises_issues` covers decorator-side failures. Live probe: decorate a function whose docstring omits one argument → decoration itself raises.

## Get live surrounding code
**Retrieve (executed 2026-08-26, project `smolagents`):**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "get_json_schema type hints json schema generation tool inputs", limit: 15 });
// rank1-2 = _get_json_schema_type :415-431, get_json_schema :97-231; tests #3/#4/#5 = TestGetJsonSchema methods; also _convert_type_hints_to_json_schema :291-323, models.get_tool_json_schema :288-329, _parse_type_hint :326-384
```

## Verdict
Adopt the docstring-as-description-source + type-hints-as-types split and the mandatory-per-arg rule — it makes tool schemas deterministic without pydantic. Adapt the regexes to your host's docstring dialect. Omit the transformers-chat-template examples; keep the `(choices:)` convention only if your prompt layer teaches it.
