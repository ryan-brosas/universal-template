<!-- capsule-v2 -->
# Memory capability: scope-qualified strip-then-inject with bounded budget and honest-failure injection

## Source / Question
`pydantic_ai_harness/memory/_capability.py` (+ `_toolset.py`) — How do you inject a persistent-memory snapshot into EVERY model request of a multi-request run without duplicating blocks, clobbering sibling memory capabilities, or letting a store outage kill the run? Porters append on every turn and end up with N stale copies in history.

## Path / Symbol
`memory/_capability.py` — `_DEFAULT_GUIDANCE` (22–33, ends "Never claim something was remembered or saved unless you actually called `write_memory` in this turn"), `<memory>` prefix/suffix + `_MEMORY_PART_METADATA = 'pydantic-ai-harness.memory.v1'` (34–36), `Memory` dataclass (45–106: agent_name is "part of the scope key only; never rendered into the model-facing block"; Temporal/Prefect caveat: injected I/O is not workflow-safe durable I/O → use `inject_memory=False` and let the integration wrap the idempotent toolset), `before_model_request` (162–240), `_remove_previous_injection` (242–269).

## Signature
```python
scope_hash = hashlib.sha256(scope.encode()).hexdigest()[:16]
marker = f'{_MEMORY_PART_METADATA}:{scope_hash}'
self._remove_previous_injection(request_context.messages, marker)   # ALWAYS before injecting
...
content_budget = self.max_tokens * 4 - len(guidance) - len(prefix) - len(suffix)
rendered = render_memory_prompt(...)[:content_budget]
request_context.messages[-1] = replace(latest, parts=[*latest.parts, UserPromptPart([TextContent(rendered, metadata=marker)])])
```

## Data Shape
Injection rides as ONE `UserPromptPart` whose content is `[TextContent(...)]` (sequence, NOT str — the marker lives in TextContent.metadata) appended to the CURRENT trailing ModelRequest only. Marker grammar: `pydantic-ai-harness.memory.v1:{scope_hash16}`. Budget knobs: max_tokens (2000 ≈ chars×4), max_lines (200), max_memory_size per-file cap, max_search_results. Span `memory.inject` records backend class, scope_hash, outcome ok/error, char counts, truncation flags.

## Decisive source
1. **Scope-qualified markers** (:168–172): several `Memory` capabilities can share one agent — each hashes its own scope so "each refreshes only their own injection instead of clobbering each other".
2. **Strip-then-inject** (:242–269): previous injections removed from ALL history requests before evaluating the new one — stateless idempotence per request. Compatibility strip ALSO matches the bare unqualified marker: "without it a resumed pre-upgrade conversation keeps one stale block permanently" (:252–256).
3. **Bounded budget math** (:204–212): content budget subtracts guidance+markers from max_tokens×4 BEFORE rendering; render receives `max(1, content_budget // 4)` then is hard-sliced to content_budget; truncation flags (`main_truncated`, `files_truncated`) are passed INTO the renderer so the model sees honest boundaries.
4. **Failure policy** (:186–199): store read/list failures record outcome=error + exception TYPE on the span, then either re-raise (`injection_errors='raise'`) or return the request untouched — degradation never fabricates empty memory.
5. **Durability boundary** (:47–53): automatic injection is explicitly NOT workflow-safe durable I/O; the static toolset is the durable-wrappable surface. Guidance text itself fights memory hallucination ("verify anything volatile", never claim a save without the call).

## Flow / Invariant
resolve scope (store resolver or default; namespace/agent segments) → hash → strip old injections everywhere → if inject_memory: read main + bounded subfile listing inside span → budget-render → append single marked part to trailing ModelRequest. Invariants: at most one injection per scope exists in history at any time; injection touches ONLY the current request (older turns stay as-sent); a missing store degrades loudly or cleanly, never silently.

## Probe (direct test)
`tests/memory/test_memory.py`: `test_agent_registers_and_executes_memory_capability` (:339), `test_toolset_has_stable_id_and_exact_schemas` (:365), `test_durable_replay_and_fingerprint_conflict` (:454), `test_mutation_requires_stable_ids` (:474), `test_oversized_external_file_is_bounded_and_not_tool_editable` (:487), `test_native_search_is_bounded_and_tenant_isolated` (:563), `test_backend_result_bounds_are_defended` (:602).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'Memory before_model_request _remove_previous_injection marker'`

## Verdict
**Adopt** scope-qualified marker strip-then-inject for ANY per-request context injection (memory, scratchpads, retrieved docs). **Adopt** budget-first rendering with visible truncation flags. **Adapt** the failure policy to your availability requirements.
