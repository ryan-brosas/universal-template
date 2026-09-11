<!-- capsule-v2 -->
# Class-body tool rules — validate_tool_attributes' ClassLevelChecker and why __init__ args must be literal-defaulted

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory project `smolagents`. **Question:** What can a Tool subclass body contain so its source can be regenerated and re-installed (Hub share + remote executor), and how is that enforced per class member?

## Path/Symbol
- `src/smolagents/tool_validation.py:validate_tool_attributes` (:157-263) with inner `ClassLevelChecker` (:172-224).
- Consumers (trace_path inbound ×6): `Tool.to_dict`, `Tool._get_tool_code`, `Tool._get_requirements`, `tools.get_tools_definition_code`, `agents.MultiStepAgent.to_dict`, `remote_executors.RemotePythonExecutor.send_tools`.

## Signature
`validate_tool_attributes(cls, check_imports: bool = True) -> None`; raises ONE aggregated `ValueError("Tool validation failed for <cls>:\n" + errors)`; returns None when clean.

## Data Shape
Rule set over the parsed ClassDef: class attributes must be literal-only (`Constant|Dict|List|Set` everywhere in the value via ast.walk); `name` must be a str Constant that is a valid identifier and non-keyword (`is_valid_name`); `__init__` params all need defaults except `self`, and defaults must be literals; methods must pass a fresh MethodChecker each.

### Decisive source
```python
# :198-202 — "complex attribute" = ANY non-literal node anywhere in the value
if not all(isinstance(val, (ast.Constant, ast.Dict, ast.List, ast.Set)) for val in ast.walk(node.value)):
    for target in node.targets:
        if isinstance(target, ast.Name):
            self.complex_attributes.add(target.id)
# :219 — trailing-alignment trick: defaults align to the LAST params only
for arg, default in reversed(list(zip_longest(reversed(node.args.args), reversed(node.args.defaults)))):
    if default is None:
        if arg.arg != "self": self.non_defaults.add(arg.arg)
    elif not isinstance(default, (ast.Constant, ast.Dict, ast.List, ast.Set)):
        self.non_literal_defaults.add(arg.arg)
# :190-192 — method bodies are NOT class attributes
def visit_Assign(self, node):
    if self.in_method: return
```

## Flow
`get_source(cls)` → `ast.parse` → require `tree.body[0]` is ClassDef → ClassLevelChecker walk (in_method context flag toggled around FunctionDef visits) → error aggregation → then one NEW MethodChecker per top-level FunctionDef seeded with discovered class_attributes, errors prefixed `- {method}: `. Rationale encoded in docstring (:160-161): init-chosen args are untraceable at source-regeneration time, hence anything important must be a class attribute — this is why complex values are pushed INTO `__init__` where instance state is reconstructed by re-instantiation, not by codegen.

## Invariant
This is the serialization gate: Hub save and remote `send_tools` both regenerate class SOURCE, so anything non-literal at class level would silently produce broken regenerated code. The zip_longest alignment is what makes "defaults apply to trailing parameters" correct for partial default lists (e.g., `(self, a, b=1)` pairs `(b,d),(a,None),(self,None)`). All findings accumulate into a single raise so authors see every violation at once.

## Probe
`tests/test_tool_validation.py`: exceptions table (:123-141) pins all five failure messages verbatim incl. non-literal module-global default `UNDEFINED_VARIABLE` (:99-110); ValidTool + @tool class twins pass (:53-55); MultipleAssignmentsTool tuple-unpack tolerance (:144-159); default-tools smoke over DuckDuckGo/Google/SpeechToText/VisitWebpage/WebSearch classes (:20-24). Live probe: add `attrs = SomeFactory.make()` as a class attribute → ValueError naming it under "Complex attributes should be defined in __init__".

## Get live surrounding code
**Retrieve (executed 2026-08-26, project `smolagents`):**
```ts
await mcp.codebase_memory.trace_path({ project: "smolagents", function_name: "validate_tool_attributes", direction: "inbound", depth: 2 });
// callers_total=6: Tool.to_dict/_get_tool_code/_get_requirements, MultiStepAgent.to_dict, RemotePythonExecutor.send_tools, get_tools_definition_code — serialization+remote-install dependence confirmed
```

## Verdict
Adopt literal-only class attributes + defaulted-literal init args as the contract for any tool/object whose SOURCE (not pickle) is the transport format. Adapt the literal set to your serializer's capabilities. Omit the AST-walk entirely if you transport pickles instead of source — but then you inherit pickle's trust requirements instead.
