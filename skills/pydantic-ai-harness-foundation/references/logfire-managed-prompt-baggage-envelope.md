<!-- capsule-v2 -->
# Logfire ManagedPrompt baggage envelope: resolve once per run, outermost, and keep the resolution span baggage-free

## Source / Question
`pydantic_ai_harness/logfire/_managed_prompt.py` (210L whole file) @ `main@f971198c` (PR #641 fixed the span-nesting invariant; Codebase Memory `pydantic-ai-harness`) — An agent's system prompt is backed by a remotely-managed, versioned/labelled/rolled-out prompt. How do you attach the selected label+version as OpenTelemetry baggage to EVERY span of the run without leaking baggage onto the resolution span itself, and what must a porter not break?

## Path / Symbol
`logfire/_managed_prompt.py` — `_PROMPT_VARIABLE_PREFIX='prompt__'` (:27; hyphens→underscores, Logfire's own convention), `ManagedPrompt.__post_init__` (:127–165), `get_ordering` (:174–176), `get_instructions` (:178–190), `wrap_run` (:192–210).

## Signature
```python
def get_ordering(self) -> CapabilityOrdering:
    return CapabilityOrdering(position='outermost', wraps=[Instrumentation])

async def wrap_run(self, ctx, *, handler):
    resolved = self._variable.get(targeting_key=..., attributes=..., label=self.label)
    with resolved:                                  # baggage context manager stays OPEN for whole run
        token = self._resolved.set(resolved)        # per-run ContextVar (concurrent-run isolation)
        try:
            return await handler()
        finally:
            self._resolved.reset(token)
```

## Data Shape
Slug → variable name `prompt__<slug>` with `-`→`_`; `default` required for slug form (`TypeError` otherwise); pre-built `Variable` accepted (then `logfire_instance` is ignored with a warning). Variable constructed DIRECTLY (not via `logfire.var`) so redeclaring the same name across agents is idempotent — the factory path registers in a per-instance registry and raises on duplicates. `targeting_key`/`attributes` accept static values or RunContext callables; instructions contribute `None` outside a run.

### Decisive source
The #641 invariant, test-pinned at `tests/logfire_variables/test_managed_prompt.py::test_baggage_propagates_to_run_and_child_spans` (:216): the "Resolve variable …" span opens BEFORE baggage attaches, so it must NOT carry the attribute — `resolution_span = spans.pop(0); assert 'logfire.variables.prompt__baggage_slug' not in resolution_span['attributes']` (:239–240). The same test's comment records WHY the rest of that span is snapshot-excluded: whether it nests under the agent run span (picking up trace-derived attrs like the `targeting_key` rollout fallback) depends on the installed pydantic-ai version — a version-dependent assertion shape porters must reproduce as a pop-and-pin, not a full snapshot. `position='outermost', wraps=[Instrumentation]` (:174–176) makes the baggage envelope the run span itself; resolution happens ONCE per run inside `wrap_run`, memoized in the ContextVar so every model request reuses one label/version decision (`test_resolved_once_per_run_across_multiple_model_requests` :323).

**Flow:** construct (validate slug→identifier, declare idempotent variable) → run starts → `wrap_run` resolves once → baggage context open around ENTIRE handler → instructions provider reads ContextVar per request → reset token in `finally`.
**Invariant:** exactly one resolution per run; baggage envelops every child span INCLUDING the model-call spans but NEVER the resolution span itself; ContextVar reset in `finally` even when the run raises; duplicate slugs across agents are legal by construction (direct `Variable(...)`, never `logfire.var`).

## Probe (direct test)
`tests/logfire_variables/test_managed_prompt.py` — baggage-free resolution span :239–240 (the #641 regression pin), run-span carries `'logfire.variables.prompt__baggage_slug': '<code_default>'` (snapshot :243+), once-per-run :323, slug normalization/warning ladder :119–157, instructions-None-outside-run :379.

## Retrieve
```
codebase-memory-mcp cli search_graph --project pydantic-ai-harness --name-pattern 'ManagedPrompt|wrap_run|get_ordering' --detail ids
```

## Verdict
Adopt the outermost-capability + resolve-once-per-run + baggage-free-resolution-span trio whenever a hosted config/prompt rides telemetry. Adapt variable naming to your host's registry rules. Omit Handlebars template rendering and Logfire-specific targeting semantics unless you ship the same platform.
