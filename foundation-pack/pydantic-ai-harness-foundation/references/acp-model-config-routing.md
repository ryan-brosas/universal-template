<!-- capsule-v2 -->
# ACP model config routing — how do you let an editor switch a session's model through a STABLE protocol surface without mutating the shared agent?

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; Codebase Memory project `pydantic-ai-harness`. **Question:** Model switching must ride ACP's stable session-config-option surface (reachable even with `use_unstable_protocol=False`), validate against exactly the advertised set, survive persistence failure, and take effect per-run — what is the full ladder from advertisement to run-time resolution?

## Path / Symbol
`pydantic_ai_harness/experimental/acp/_adapter.py` — `_MODEL_CONFIG_ID = 'model'` (:79), `set_config_option` (:910–925), `_model_option` (:404–414), `_model_config_options` (:416–421), `_resolve_run_model` (:896–903); session state field `SessionState.model: str | None` (`_session.py` :93–108, comment :101–103).

**Signature:**
```python
async def set_config_option(self, config_id: str, session_id: str, value: str | bool,
                            **kwargs) -> schema.SetSessionConfigOptionResponse | None
def _model_option(self, current_model_id: str | None) -> schema.SessionConfigOptionSelect | None
def _resolve_run_model(self, model_id: str | None) -> Model | str | None
```

**Data Shape:** One select option advertised per session: `id='model'`, `type='select'`, `current_value=<selected id>`, options = the configured `models` list (ids verbatim). `SessionState.model` holds the client's choice; `None` = use the agent's own model. Advertisement exists only when models are configured AND a selection/current value exists (`_model_config_options` returns `None` otherwise).

### Decisive source
```python
        if config_id != _MODEL_CONFIG_ID:
            raise acp.RequestError.invalid_params({'config_id': config_id, 'reason': 'unknown config option'})
        if not isinstance(value, str) or value not in self._models:
            raise acp.RequestError.invalid_params({'model_id': value, 'reason': 'not an advertised model'})
        state.model = value
        await self._persist(state)
        options = self._model_config_options(state.model)
        assert options is not None
        return schema.SetSessionConfigOptionResponse(config_options=options)
```
And the run seam (:896–903): "`None` (no advertised models) is passed through so the run uses the agent's own model." → in `_run_turn`: `model=self._resolve_run_model(state.model)` with the comment "Per-run override for the client's model config choice; `None` uses the agent's own model, never mutating the shared agent. A `model_resolver` (if given) maps the advertised id to a pre-built `Model` for ids `infer_model` can't parse."

**Flow:** initialize/new_session/load_session advertise the option when models are configured → client picks → validation ladder (known config id → advertised string id) → `state.model = value` → immediate best-effort `_persist` (store failure logged; in-memory selection stands — test_set_model_config_save_failure_is_logged_and_does_not_fail_the_request) → response echoes refreshed options → every run resolves `state.model` through `_resolve_run_model` as a per-run `model=` kwarg. Stored sessions restore `stored.model` so a reopened session keeps its pick.

**Invariant:** The shared pydantic-ai Agent is NEVER mutated by client choices — switching is per-session state consumed at run time. Only advertised ids validate; unknown ids/configs are malformed input (`invalid_params`), unsupported methods stay `method_not_found` — the JSON-RPC error CODE distinguishes malformed from unroutable (TestErrorCodes). The routing works over the stable surface alone (conformance test runs with `unstable=False`).

**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pydantic-ai-harness && /tmp/harness-p6-venv/bin/python -m pytest "tests/experimental/acp/test_conformance.py::TestModelConfigRouting" "tests/experimental/acp/test_conformance.py::TestErrorCodes" "tests/experimental/acp/test_persistence.py::test_set_model_config_save_failure_is_logged_and_does_not_fail_the_request" -q'` — stable-surface routing asserts `SessionConfigOptionSelect.current_value == 'test'`; error codes pinned; failing store keeps the selection. (Executed this pass; see verification.md.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "set_config_option _MODEL_CONFIG_ID SessionConfigOptionSelect model_resolver", limit: 5 });
```
Observed live: rank#1 `TestModelConfigRouting.test_set_config_option_routes_without_unstable_protocol` (tests/experimental/acp/test_conformance.py :103–111); `set_config_option` (_adapter.py :910–925) and `_MODEL_CONFIG_ID` (:79) adjacent.

## Verdict
**Adopt** per-session selected-model state resolved at run time for any multi-model agent server — never rebuild or mutate the shared agent per request; keep the optional resolver hook for ids your framework cannot infer. **Adopt** advertising exactly one stable config option and echoing the refreshed list after each change. **Adopt** persisting the selection best-effort so durability lag never fails the switch. **Adapt** the option vocabulary to your protocol's config surface. **Omit** ACP unstable-method gating details (covered by next-pass stdio entry target). Caveat: none — conformance + error-code + persistence tests pin it at this pin.
