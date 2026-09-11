<!-- capsule-v2 -->
# skip-user-inputs-trigger-key — How do trigger-driven runs bypass user-input preparation without a flag parameter explosion?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the sanctioned way to skip `_prepare_user_inputs` for machine-originated invocations?

## Sentinel args key checked by the generator, stripped of typing guarantees
**Path/Symbol:** `api/core/app/apps/workflow/app_generator.py:SKIP_PREPARE_USER_INPUTS_KEY` (:61), `_should_prepare_user_inputs` (:92-94), gate at :206-212; FIXME comment at :204-205.
**Signature:** `_should_prepare_user_inputs(args: Mapping[str, Any]) -> bool`.
**Data Shape:** `"args"` is an untyped Mapping from controllers; sentinel value = any truthy entry under key `"_skip_prepare_user_inputs"`.

### Decisive source
```python
SKIP_PREPARE_USER_INPUTS_KEY = "_skip_prepare_user_inputs"

@staticmethod
def _should_prepare_user_inputs(args: Mapping[str, Any]) -> bool:
    return not bool(args.get(SKIP_PREPARE_USER_INPUTS_KEY))

def generate(self, *, app_model, workflow, user, args, invoke_from, ...):
    ...
    inputs: Mapping[str, Any] = args["inputs"]
    ...
    # FIXME (Yeuoly): we need to remove the SKIP_PREPARE_USER_INPUTS_KEY from the args
    # trigger shouldn't prepare user inputs
    if self._should_prepare_user_inputs(args):
        inputs = self._prepare_user_inputs(
            user_inputs=inputs,
            variables=app_config.variables,
            tenant_id=app_model.tenant_id,
            strict_type_validation=True if invoke_from == InvokeFrom.SERVICE_API else False,
        )
```

**Flow:** caller (trigger dispatcher) injects the sentinel into args → generate() skips form-schema validation/coercion entirely → raw trigger payload flows to the variable pool. Human-facing paths (web/API) never set the key and get full validation.
**Invariant:** Skipping preparation means NO required-checks, NO type coercion, NO file conversion — only machine callers with pre-validated payloads may use it; strictness still varies by invoke source (SERVICE_API gets strict validation when it DOES prepare); upstream tracks removal of this escape hatch as tech debt (in-source FIXME).
**Probe:** `grep -c 'SKIP_PREPARE_USER_INPUTS_KEY' core/app/apps/workflow/app_generator.py` → 3; direct test `tests/unit_tests/core/app/apps/test_workflow_app_generator.py::test_should_prepare_user_inputs_keeps_validation_when_flag_false`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "WorkflowAppGenerator _should_prepare_user_inputs skip flag trigger", limit: 10 });
```

## Verdict
Adopt the sentinel-key pattern for opt-out of input pipelines (and its documented danger). Adapt where the key lives (constants module). Omit the FIXME state — in YOUR port, prefer an explicit typed parameter over args smuggling; port the behavior, note the debt.
