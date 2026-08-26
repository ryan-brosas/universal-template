<!-- capsule-v2 -->
# Durable model round-trip — only strings cross the boundary, and unregistered instances must fail loud

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/_base.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A durable engine (Temporal/DBOS/Prefect) can't serialize a live `Model` into an activity/step/task — how do you carry model identity across the boundary WITHOUT letting a rebuild silently point at a different endpoint with different credentials? A porter will serialize `model_id` and rebuild it, quietly dropping a tenant's `base_url` and API key.

## Path / Symbol
`durable_exec/_base.py` — `BaseDurabilityCapability` (:40+), `_bind_models` (:348–380), `resolve_model_id` (:382–397), `_model_id_for_request` (:399–419), `_find_model_id` (:421–456), `_resolve_model_for_request` (:458–494), `_model_rebuild_escape_hatches` (:496–502).

## Signature
```python
def _model_id_for_request(ctx, request_context) -> str | None   # provenance string or registry key
def _find_model_id(model: Model) -> str | None                  # None = default; key = models= entry; else RAISES
async def _resolve_model_for_request(model_id: str | None, run_context) -> Model
def resolve_model_id(ctx, *, model_id: str) -> Model | None     # registry backstop; None defers down the chain
```

## Data Shape
Registry `_models_by_id: dict[str, Model]` built at bind time: concrete default registered as `'default'` (reserved key), each `models=` entry also under its raw string. A plain-string agent default is deliberately NOT resolved eagerly — eager construction could build the wrong provider with auth side effects before a sibling `ResolveModelId` reinterprets it; instead every request for the default carries the raw string.

### Decisive source — shallowest-match wrapper peel then hard rejection (:444–455)
```python
candidate = model
while candidate is not None:
    for model_id, registered in self._models_by_id.items():
        if registered is candidate:
            return None if model_id == 'default' else model_id
    candidate = candidate.wrapped if isinstance(candidate, WrapperModel) else None
raise UserError(f'The model instance {model.model_id!r} was not registered ... rebuilding it from its '
    "`model_id` would build a different model — the same model name on whatever provider the worker's "
    'environment implies — so the request would quietly go to another endpoint with other credentials. '
    + escape hatches)
```
Provenance preference: if the request still targets the run's model (`unwrap_model(request_context.model) is unwrap_model(run_model)`), return `ModelRequestContext.model_id` — it survives aliases the resolved model's own id doesn't; an outer capability's model swap invalidates provenance → fall back to `_find_model_id`.

**Flow:** workflow side stamps `str | None` into the durable-unit input → unit side `_resolve_model_for_request`: `None` → registry `'default'`; else full deps-aware `root_capability.resolve_model_id` chain FIRST (user resolvers get first crack; their exceptions propagate unchanged), `infer_model` backstop last, its errors translated to escape-hatch guidance.

**Invariant:** Only strings cross; an instance matching nothing is REJECTED rather than round-tripped as its own `model_id` (rebuilding would reach another endpoint). The registered side is never unwrapped — a registered wrapper keeps its own ID at its registered depth even under further unregistered wrapping (e.g. `InstrumentedModel` around it).

**Probe:** `tests/test_dbos.py::test_dbos_durability_unregistered_model_instance_errors` (:3030, byte-exact error snapshot naming the dropped tenant base_url/credentials), `test_dbos_durability_unrebuildable_model_string_errors` (:3056 region); `tests/test_temporal.py::test_temporal_agent_run_in_workflow_with_model` (:2972).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query '_find_model_id _models_by_id _resolve_model_for_request WrapperModel peel'
```

## Verdict
**Adopt** the string-only boundary, reserved-default registry, shallowest-match peel, provenance-vs-swap rule, and the loud rejection with credential-leak explanation verbatim for any host that spans a serialization boundary. **Adapt** engine nouns in messages and your resolver-chain equivalent. **Omit** per-engine activity configs (engine-specific subclasses).
