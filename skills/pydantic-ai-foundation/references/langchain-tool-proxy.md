<!-- capsule-v2 -->
# LangChain tool proxy — defaults re-derived from the args schema, required recomputed, additionalProperties forced

## Source / Question
`pydantic_ai_slim/pydantic_ai/ext/langchain.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you adapt a foreign tool object (LangChain's duck-typed `args`/`run` protocol) into your native tool type without re-deriving its schema — and what must you fix about a LangChain schema for strict-mode providers? A porter will pass the schema through untouched and ship `additionalProperties` unset, which strict providers reject.

## Path / Symbol
`ext/langchain.py` — `tool_from_langchain` (:32–64), `LangChainTool` Protocol (:11–26), `LangChainToolset` (:67–71).

## Signature
```python
class LangChainTool(Protocol):
    @property
    def args(self) -> dict[str, JsonSchemaValue]: ...      # per-param detail dicts incl. 'default'
    def get_input_jsonschema(self) -> JsonSchemaValue: ...
    def run(self, *args: Any, **kwargs: Any) -> str: ...
def tool_from_langchain(langchain_tool: LangChainTool) -> Tool
```

## Data Shape
Two parallel sources of truth: `args` (property-level param details, used to derive `required` and defaults) and `get_input_jsonschema()` (the wire schema). Required is recomputed as every name whose detail lacks `'default'`, SORTED; defaults extracted into a flat dict.

### Decisive source — schema patch + kwargs-only proxy (:43–57)
```python
inputs = langchain_tool.args.copy()
required = sorted({name for name, detail in inputs.items() if 'default' not in detail})
schema: JsonSchemaValue = langchain_tool.get_input_jsonschema()
if 'additionalProperties' not in schema:
    schema['additionalProperties'] = False        # strict-mode providers require this closed
if required:
    schema['required'] = required
defaults = {name: detail['default'] for name, detail in inputs.items() if 'default' in detail}

def proxy(*args: Any, **kwargs: Any) -> str:
    assert not args, 'This should always be called with kwargs'
    kwargs = defaults | kwargs                    # model-supplied values override LC defaults
    return langchain_tool.run(kwargs)
```
The proxy is registered via `Tool.from_schema` with the patched schema, bypassing signature introspection entirely. `LangChainToolset.__init__` just maps `tool_from_langchain` over a list into a `FunctionToolset`.

**Flow:** wrap → patch schema (close additionalProperties, set sorted required) → at call time merge LC defaults under model kwargs positionally-independent → forward single dict to `tool.run`.

**Invariant:** The host never calls `run` positionally (assert); defaults live in the PROXY closure, not in the schema's `default` keywords; only fill in `'required'` when non-empty.

**Probe:** `tests/ext/test_langchain.py::test_langchain_tool_conversion` (:44), `test_langchain_tool_no_additional_properties` (:84 — missing key gets added), `test_langchain_tool_conversion_no_defaults` (:104 — everything becomes required), `test_langchain_tool_conversion_no_required` (:128 — no `required` key when all defaulted), `test_langchain_tool_defaults` (:152), `test_langchain_tool_positional` (:180 — assert fires), `test_langchain_tool_default_override` (:196).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'tool_from_langchain get_input_jsonschema additionalProperties defaults'
```

## Verdict
**Adopt** the two-source-of-truth adaptation, schema-closing rule, sorted-required derivation, and defaults-in-proxy pattern for any Protocol-duck-typed foreign tool. **Adapt** the target tool constructor (`Tool.from_schema`). **Omit** nothing — 71 lines.
