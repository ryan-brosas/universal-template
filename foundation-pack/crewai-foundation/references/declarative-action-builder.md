<!-- capsule-v2 -->
# Declarative action builder — how does one `do:` key in YAML dispatch to code, tools, crews, agents, expressions, scripts, or each-loops at runtime?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What is the action-type registry contract, and how do nested steps receive loop-local context?

## isinstance ladder over definition types + local-context kwarg
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/_actions.py` (`build_action` :352–360, `_ACTION_TYPES` :341–350, `EachAction` :262–338, `ScriptAction` :216–260, `_pop_local_context` :396–407, `_resolve_crew_declaration` :409–434).
**Signature:** `build_action(flow: Flow[Any], definition: FlowActionDefinition) -> Callable[..., Any]`.
**Data Shape:** `_LOCAL_CONTEXT_KWARG = "__flow_definition_local_context"`; script gate env `CREWAI_ALLOW_FLOW_SCRIPT_EXECUTION` ∈ {"1","true","yes"}.

### Decisive source
```python
_ACTION_TYPES: tuple[_ActionType, ...] = (
    EachAction,   # FIRST — must precede others for list-of-steps defs
    CodeAction,
    ToolAction,
    AgentAction,
    CrewAction,
    ExpressionAction,
    ScriptAction,
)
```
```python
class ScriptAction:
    def _compile_handler(self):
        raw = os.environ.get(_ALLOW_SCRIPT_EXECUTION_ENV_VAR, "")
        if raw.strip().lower() not in _TRUSTED_SCRIPT_EXECUTION_VALUES:
            raise FlowScriptExecutionDisabledError(...)
        module = ast.parse(self.definition.code, filename=filename)
        function = ast.FunctionDef(
            name="_flow_script",
            args=ast.arguments(args=[ast.arg(arg) for arg in
                              ("state", "outputs", "input", "item")], ...),
            body=module.body or [ast.Pass()], ...)
```

**Flow:** build wraps the matching action class (first isinstance match wins) → run receives a hidden local-context kwarg that `_pop_local_context` strips so plain methods never see it → EachAction evaluates `in:` to a list (non-list ⇒ ValueError), then per item runs ordered sub-steps honoring CEL `if:` conditions, accumulating step outputs locally and returning LAST output per item → CrewAction resolves declaration paths ONLY inside the flow-definition directory (`is_relative_to` check) preferring crew.jsonc → scripts compile trusted YAML code into a 4-arg function, disabled unless env-opted.
**Invariant:** EachAction ordering in the tuple is semantic — list-shaped definitions would otherwise mis-dispatch. Local context rides ONE reserved kwarg through every layer including thread hops via `contextvars.copy_context()`. Script execution is arbitrary-code-by-design and therefore default-off with explicit opt-in.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow_from_definition.py::test_script_action_requires_explicit_opt_in" -q` (expect 1 passed); static anchors: `CREWAI_ALLOW_FLOW_SCRIPT_EXECUTION` ×2, `is_relative_to(resolved_base_dir)` ×1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "build_action script action disabled env var compile ast each action", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ordered isinstance registry plus reserved-kwarg context passing; adapt the CEL expression layer to your template engine; omit ScriptAction entirely unless you need YAML-native compute. Direct test executed green at pin.
