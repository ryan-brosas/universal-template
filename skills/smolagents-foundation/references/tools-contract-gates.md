<!-- capsule-v2 -->
# Tool contract & validation gates — what makes a Tool serializable, callable, and schema-true?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** Which invariants does a Tool subclass satisfy at class-definition time, at call time, and at serialization time — and why is validation wired into `__init_subclass__`?

## Validate-on-subclass, sanitize-on-call
**Path/Symbol:** `src/smolagents/tools.py:Tool` (:106-249: `__init_subclass__` :140-142, `validate_arguments` :144-226, `__call__` :231-249), `validate_after_init` (:70-79), `AUTHORIZED_TYPES` (:82-93), `validate_tool_arguments` (:1361-1412); static analysis in `tool_validation.py:MethodChecker/validate_tool_attributes`.
**Signature:** Subclass must define class attrs `name:str, description:str, inputs:dict[str,{type,description}], output_type:str`; `forward(self, ...)` params MUST equal `inputs.keys()`; optional `skip_forward_signature_validation=True` for wrapper tools.
**Data Shape:** `inputs[*]["type"]` is one string or list of strings from the closed vocab {string, boolean, integer, number, image, audio, array, object, any, null}; `nullable:True` marks optional.

### Decisive source
```python
def __init_subclass__(cls, **kwargs):        # :140 — every subclass validated AT DEFINITION
    super().__init_subclass__(**kwargs)
    validate_after_init(cls)                 # wraps __init__ to also run validate_arguments()

# :203-210 — signature/schema bijection:
actual_keys = set(key for key in signature.parameters.keys() if key != "self")
expected_keys = set(self.inputs.keys())
if actual_keys != expected_keys: raise Exception(...)
```

**Flow:** Definition time: attribute presence/type checks, identifier-and-not-keyword name rule (`is_valid_name`), closed type vocab, forward-signature ↔ inputs equality, nullable cross-checks between inputs and type hints. Serialization time (`to_dict`): SimpleTools (@tool) re-extract forward source with self-argument injection and decorator stripping; subclassed tools go through `validate_tool_attributes` (init args need literal defaults; no complex class attributes; MethodChecker flags undefined names/local imports per method) then `instance_to_source`; requirements derived by AST import scan minus stdlib plus "smolagents". Call time: single-dict positional → kwargs conversion when keys match inputs; lazy `setup()` on first call; `sanitize_inputs_outputs` routes AgentImage/AgentAudio wrapping. Argument validation allows int→number coercion and `"any"` wildcard but rejects unknown keys, missing requireds, and wrong types.
**Invariant:** The three checkpoints are redundant ON PURPOSE: definition-time catches authoring bugs before any LLM sees the tool; serialization-time guarantees round-trip fidelity (a tool whose code can't regenerate itself breaks Hub sharing AND remote-executor tool installation); call-time guards only against runtime model misbehavior. Dropping any one layer moves failures to production.
**Probe:** `tests/test_tools.py::test_validate_tool_arguments*` (:954, :1035), `tests/test_tool_validation.py` (:23-179 incl. multiple-assignments case), `test_function_type_hints_utils.py::TestGetJsonSchema` (:282+). Live: subclass missing an input key fails at class creation; int arg into `number` input passes validate_tool_arguments.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "validate_arguments __init_subclass__ AUTHORIZED_TYPES validate_tool_attributes", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt validate-at-definition + serialize-roundtrip + sanitize-at-call as three separate gates. Adapt the type vocabulary and requirement scanner to your host. Omit `__init_subclass__` wiring and invalid tools surface only when an agent first calls them.
